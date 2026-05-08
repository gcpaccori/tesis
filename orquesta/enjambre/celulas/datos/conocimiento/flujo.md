# Celula de Datos

        Plantilla universal de especialidad con aislamiento de flujo.

        ## Roles simbolicos
        - Subgerente: Subgerente de Trafico y Datos
        - Supervisor: Supervisor Datos
        - Especialista Principal: Avatar de Datos
        - Secretario: Secretario Datos
        - Auditor: Auditor de Esquema

        ## Enfoque
        - Division: subgerencia-trafico-datos
        - Foco: esquemas, tablas, llaves y mutaciones semanales
        - Herramienta visible: Schema

        ## Oraculos y dependencias
        - avatar-datos
- oraculo-maestro

        ## Soportes de la celula
        - grafo-herramientas

        ## Asistentes efimeros
        - DB-1: asistente efimero para trabajo paralelo
- DB-2: asistente efimero para trabajo paralelo
- DB-3: asistente efimero para trabajo paralelo
- DB-4: asistente efimero para trabajo paralelo

        ## Regla operativa
        - El Supervisor responde al mundo sin interrumpir al Especialista.
        - El Secretario mata loops, timeouts y deltas muertos.
        - El Auditor destila soluciones limpias y solo sube oro al grafo maestro.
