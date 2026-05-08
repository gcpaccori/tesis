from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import networkx as nx

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
DEFAULT_DB_PATH = DATA_DIR / "memoria_orquesta.sqlite3"
DEFAULT_GRAPHML_PATH = LOGS_DIR / "memoria_orquesta.graphml"

STOPWORDS = {
    "a",
    "al",
    "algo",
    "con",
    "como",
    "de",
    "del",
    "el",
    "en",
    "es",
    "esta",
    "este",
    "hay",
    "la",
    "las",
    "lo",
    "los",
    "mi",
    "para",
    "por",
    "que",
    "quiero",
    "se",
    "sin",
    "su",
    "un",
    "una",
    "ya",
    "y",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(value: Optional[Union[Dict[str, Any], List[Any]]]) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True)


def _json_loads(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {"raw": value}


def _clean_text(value: str, max_len: int = 400) -> str:
    text = re.sub(r"\s+", " ", (value or "").strip())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _tokenize(value: str) -> list[str]:
    raw_tokens = re.findall(r"[a-zA-Z0-9_-]+", value.lower())
    tokens = [token for token in raw_tokens if token not in STOPWORDS and len(token) > 2]
    return tokens[:12]


@dataclass
class MemoryResult:
    nodes: List[Dict[str, Any]]
    memories: List[Dict[str, Any]]
    relations: List[str]

    def to_prompt_block(self) -> str:
        if not self.nodes and not self.memories and not self.relations:
            return "Sin memoria relevante previa."

        lines = []
        if self.nodes:
            lines.append("Nodos relevantes:")
            for node in self.nodes[:5]:
                lines.append(
                    f"- {node['name']} [{node['type']}]: {node.get('description', 'sin descripcion')}"
                )
        if self.memories:
            lines.append("Memorias previas:")
            for item in self.memories[:4]:
                lines.append(f"- {item['summary']}")
        if self.relations:
            lines.append("Relaciones del grafo:")
            for relation in self.relations[:6]:
                lines.append(f"- {relation}")
        return "\n".join(lines)


class MemoriaGrafo:
    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        graphml_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.graphml_path = Path(graphml_path or DEFAULT_GRAPHML_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.graphml_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    type TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL,
                    target_id INTEGER NOT NULL,
                    relation TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 1.0,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (source_id) REFERENCES nodes(id),
                    FOREIGN KEY (target_id) REFERENCES nodes(id)
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memory_links (
                    memory_id INTEGER NOT NULL,
                    node_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    UNIQUE(memory_id, node_id, role),
                    FOREIGN KEY (memory_id) REFERENCES memories(id),
                    FOREIGN KEY (node_id) REFERENCES nodes(id)
                );
                CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
                CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
                CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
                CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id);
                CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);
                """
            )

    def _upsert_node(
        self,
        conn: sqlite3.Connection,
        name: str,
        node_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        timestamp = _utc_now()
        clean_name = _clean_text(name, max_len=180)
        if not clean_name:
            raise ValueError("Node name cannot be empty")

        existing = conn.execute(
            "SELECT id, type, metadata_json FROM nodes WHERE name = ?",
            (clean_name,),
        ).fetchone()
        if existing:
            merged_metadata = _json_loads(existing["metadata_json"])
            merged_metadata.update(metadata or {})
            resolved_type = node_type
            if existing["type"] != "Concepto" and node_type == "Concepto":
                resolved_type = existing["type"]
            elif existing["type"] == "Concepto" and node_type != "Concepto":
                resolved_type = node_type
            conn.execute(
                """
                UPDATE nodes
                SET type = ?, metadata_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (resolved_type, _json_dumps(merged_metadata), timestamp, existing["id"]),
            )
            return int(existing["id"])

        cursor = conn.execute(
            """
            INSERT INTO nodes (name, type, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (clean_name, node_type, _json_dumps(metadata), timestamp, timestamp),
        )
        return int(cursor.lastrowid)

    def _add_edge(
        self,
        conn: sqlite3.Connection,
        source_id: int,
        target_id: int,
        relation: str,
        metadata: Optional[Dict[str, Any]] = None,
        weight: float = 1.0,
    ) -> None:
        conn.execute(
            """
            INSERT INTO edges (source_id, target_id, relation, weight, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (source_id, target_id, relation, weight, _json_dumps(metadata), _utc_now()),
        )

    def registrar_turno(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        route: List[str],
        specialist_notes: Dict[str, str],
        memory_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = memory_payload or {}
        summary = _clean_text(payload.get("summary") or assistant_message, max_len=220)
        decisions = payload.get("decisions") or []
        open_loops = payload.get("open_loops") or []
        entities = payload.get("entities") or []
        relations = payload.get("relations") or []

        metadata = {
            "route": route,
            "specialist_notes": specialist_notes,
            "decisions": decisions,
            "open_loops": open_loops,
        }

        with self._connect() as conn:
            memory_cursor = conn.execute(
                """
                INSERT INTO memories (session_id, kind, summary, content, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    "turno",
                    summary,
                    json.dumps(
                        {
                            "user_message": user_message,
                            "assistant_message": assistant_message,
                        },
                        ensure_ascii=False,
                    ),
                    _json_dumps(metadata),
                    _utc_now(),
                ),
            )
            memory_id = int(memory_cursor.lastrowid)

            session_node_id = self._upsert_node(
                conn,
                f"sesion:{session_id}",
                "Sesion",
                {"session_id": session_id},
            )
            memory_node_id = self._upsert_node(
                conn,
                f"turno:{memory_id}",
                "Memoria",
                {"summary": summary, "session_id": session_id},
            )
            self._add_edge(conn, session_node_id, memory_node_id, "contiene_turno")

            route_node_ids = []
            for role in route:
                route_node_ids.append(
                    self._upsert_node(
                        conn,
                        role,
                        "Rol",
                        {"kind": "especialista_liquido"},
                    )
                )
            for role_id in route_node_ids:
                self._add_edge(conn, memory_node_id, role_id, "activo_en_turno")

            linked_nodes = []
            for entity in entities:
                node_id = self._upsert_node(
                    conn,
                    entity.get("name", ""),
                    entity.get("type", "Concepto"),
                    entity.get("metadata") or {"description": entity.get("description", "")},
                )
                linked_nodes.append(node_id)
                conn.execute(
                    "INSERT OR IGNORE INTO memory_links (memory_id, node_id, role) VALUES (?, ?, ?)",
                    (memory_id, node_id, "menciona"),
                )
                self._add_edge(conn, memory_node_id, node_id, "menciona")

            for decision in decisions:
                decision_id = self._upsert_node(
                    conn,
                    decision,
                    "Decision",
                    {"session_id": session_id},
                )
                linked_nodes.append(decision_id)
                conn.execute(
                    "INSERT OR IGNORE INTO memory_links (memory_id, node_id, role) VALUES (?, ?, ?)",
                    (memory_id, decision_id, "decision"),
                )
                self._add_edge(conn, memory_node_id, decision_id, "define")

            for pending in open_loops:
                pending_id = self._upsert_node(
                    conn,
                    pending,
                    "Pendiente",
                    {"session_id": session_id},
                )
                linked_nodes.append(pending_id)
                conn.execute(
                    "INSERT OR IGNORE INTO memory_links (memory_id, node_id, role) VALUES (?, ?, ?)",
                    (memory_id, pending_id, "pendiente"),
                )
                self._add_edge(conn, memory_node_id, pending_id, "deja_abierto")

            for relation in relations:
                source_name = relation.get("source")
                target_name = relation.get("target")
                relation_type = relation.get("type")
                if not source_name or not target_name or not relation_type:
                    continue
                source_id = self._upsert_node(conn, source_name, "Concepto")
                target_id = self._upsert_node(conn, target_name, "Concepto")
                self._add_edge(conn, source_id, target_id, relation_type, relation.get("metadata"))

            conn.commit()

        self.exportar_graphml()
        return {
            "memory_id": memory_id,
            "summary": summary,
            "linked_nodes": len(set(linked_nodes)),
        }

    def buscar(self, query: str, limit: int = 5) -> MemoryResult:
        tokens = _tokenize(query)
        if not tokens:
            tokens = [query.lower().strip()] if query.strip() else []

        with self._connect() as conn:
            node_rows = conn.execute(
                """
                SELECT id, name, type, metadata_json, updated_at
                FROM nodes
                ORDER BY updated_at DESC
                LIMIT 200
                """
            ).fetchall()
            scored_nodes = []
            for row in node_rows:
                metadata = _json_loads(row["metadata_json"])
                searchable = " ".join(
                    [
                        str(row["name"]),
                        str(row["type"]),
                        json.dumps(metadata, ensure_ascii=False),
                    ]
                ).lower()
                score = sum(token in searchable for token in tokens)
                if score:
                    scored_nodes.append(
                        {
                            "id": int(row["id"]),
                            "name": row["name"],
                            "type": row["type"],
                            "description": _clean_text(
                                metadata.get("description")
                                or metadata.get("summary")
                                or json.dumps(metadata, ensure_ascii=False),
                                max_len=140,
                            ),
                            "score": score,
                        }
                    )
            scored_nodes.sort(key=lambda item: (-item["score"], item["name"]))
            selected_nodes = scored_nodes[:limit]

            memory_rows = conn.execute(
                """
                SELECT id, session_id, summary, content, metadata_json, created_at
                FROM memories
                ORDER BY created_at DESC
                LIMIT 200
                """
            ).fetchall()
            scored_memories = []
            for row in memory_rows:
                searchable = f"{row['summary']} {row['content']} {row['metadata_json']}".lower()
                score = sum(token in searchable for token in tokens)
                if score:
                    scored_memories.append(
                        {
                            "id": int(row["id"]),
                            "session_id": row["session_id"],
                            "summary": _clean_text(row["summary"], max_len=180),
                            "created_at": row["created_at"],
                            "score": score,
                        }
                    )
            scored_memories.sort(key=lambda item: (-item["score"], item["created_at"]), reverse=True)
            selected_memories = scored_memories[:limit]

            relations = []
            if selected_nodes:
                node_ids = [node["id"] for node in selected_nodes]
                placeholders = ",".join("?" for _ in node_ids)
                edge_rows = conn.execute(
                    f"""
                    SELECT
                        src.name AS source_name,
                        tgt.name AS target_name,
                        edges.relation AS relation
                    FROM edges
                    JOIN nodes src ON src.id = edges.source_id
                    JOIN nodes tgt ON tgt.id = edges.target_id
                    WHERE edges.source_id IN ({placeholders})
                       OR edges.target_id IN ({placeholders})
                    ORDER BY edges.id DESC
                    LIMIT 24
                    """,
                    tuple(node_ids + node_ids),
                ).fetchall()
                for row in edge_rows:
                    relations.append(f"{row['source_name']} -[{row['relation']}]-> {row['target_name']}")

        return MemoryResult(
            nodes=selected_nodes,
            memories=selected_memories,
            relations=relations[:limit + 1],
        )

    def estadisticas(self) -> Dict[str, Any]:
        with self._connect() as conn:
            node_count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            edge_count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            memory_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        return {
            "db_path": str(self.db_path),
            "graphml_path": str(self.graphml_path),
            "nodes": node_count,
            "edges": edge_count,
            "memories": memory_count,
        }

    def exportar_graphml(self) -> None:
        with self._connect() as conn:
            graph = nx.MultiDiGraph()
            for row in conn.execute("SELECT id, name, type, metadata_json FROM nodes"):
                graph.add_node(
                    str(row["id"]),
                    label=row["name"],
                    type=row["type"],
                    metadata=row["metadata_json"],
                )
            for row in conn.execute(
                """
                SELECT id, source_id, target_id, relation, weight, metadata_json
                FROM edges
                """
            ):
                graph.add_edge(
                    str(row["source_id"]),
                    str(row["target_id"]),
                    key=str(row["id"]),
                    relation=row["relation"],
                    weight=float(row["weight"]),
                    metadata=row["metadata_json"],
                )
        nx.write_graphml(graph, self.graphml_path)
