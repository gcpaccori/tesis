import copy
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import MetaData, Table, create_engine, insert, select, update


FLOW_NAME = os.environ.get("FLOW_NAME", "QA Electro Sur - Pipeline Real")
ARCHIVE_PREFIX = "ARCHIVADO NO USAR - "


def main() -> None:
    database_url = os.environ["LANGFLOW_DATABASE_URL"]
    engine = create_engine(database_url)
    metadata = MetaData()
    user_table = Table("user", metadata, autoload_with=engine)
    folder_table = Table("folder", metadata, autoload_with=engine)
    flow_table = Table("flow", metadata, autoload_with=engine)

    with engine.begin() as conn:
        user_row = conn.execute(select(user_table.c.id).where(user_table.c.username == "langflow")).mappings().first()
        if not user_row:
            raise RuntimeError("No encontre usuario langflow.")
        folder_row = conn.execute(select(folder_table.c.id).where(folder_table.c.user_id == user_row["id"]).limit(1)).mappings().first()
        if not folder_row:
            raise RuntimeError("No encontre carpeta de LangFlow.")

        existing_rows = conn.execute(
            select(flow_table.c.id, flow_table.c.name).where(
                flow_table.c.user_id == user_row["id"],
                flow_table.c.name == FLOW_NAME,
            )
        ).mappings().all()
        if not existing_rows:
            raise RuntimeError(f"No encontre flow base {FLOW_NAME!r} para clonar.")

        base_row = conn.execute(
            select(
                flow_table.c.id,
                flow_table.c.data,
                flow_table.c.description,
                flow_table.c.icon,
                flow_table.c.icon_bg_color,
                flow_table.c.gradient,
                flow_table.c.tags,
            ).where(flow_table.c.id == existing_rows[0]["id"])
        ).mappings().first()
        data = copy.deepcopy(base_row["data"])
        description = (base_row["description"] or "") + " Fresh ID para evitar cache de canvas viejo."

        for row in existing_rows:
            archived_name = f"{ARCHIVE_PREFIX}{FLOW_NAME} - {str(row['id'])[:8]}"
            conn.execute(
                update(flow_table)
                .where(flow_table.c.id == row["id"])
                .values(name=archived_name, updated_at=datetime.now(timezone.utc))
            )

        new_id = uuid.uuid4()
        conn.execute(
            insert(flow_table).values(
                id=new_id,
                user_id=user_row["id"],
                folder_id=folder_row["id"],
                name=FLOW_NAME,
                description=description,
                icon=base_row["icon"],
                icon_bg_color=base_row["icon_bg_color"],
                gradient=base_row["gradient"],
                is_component=False,
                updated_at=datetime.now(timezone.utc),
                webhook=False,
                endpoint_name=None,
                data=data,
                mcp_enabled=False,
                action_name=None,
                action_description=None,
                access_type="PRIVATE",
                tags=base_row["tags"],
                locked=False,
                fs_path=None,
            )
        )

    print({"status": "ok", "new_flow_id": str(new_id), "flow_name": FLOW_NAME, "archived": len(existing_rows)})


if __name__ == "__main__":
    main()
