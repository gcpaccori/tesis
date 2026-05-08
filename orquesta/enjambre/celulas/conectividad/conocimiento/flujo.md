# Celula de Integracion

        Plantilla universal de especialidad con aislamiento de flujo.

        ## Roles simbolicos
        - Subgerente: Subgerente de Trafico y Datos
        - Supervisor: Supervisor Conectividad
        - Especialista Principal: Fontanero de Integracion
        - Secretario: Secretario Conectividad
        - Auditor: Auditor DAL

        ## Enfoque
        - Division: subgerencia-trafico-datos
        - Foco: DAL, paquetes, connection strings y pooling
        - Herramienta visible: Wire

        ## Oraculos y dependencias
        - avatar-datos
- oraculo-maestro

        ## Soportes de la celula
        - arquitecto-liquido

        ## Asistentes efimeros
        - NET-1: asistente efimero para trabajo paralelo
- NET-2: asistente efimero para trabajo paralelo
- NET-3: asistente efimero para trabajo paralelo
- NET-4: asistente efimero para trabajo paralelo
- NET-5: asistente efimero para trabajo paralelo

        ## Regla operativa
        - El Supervisor responde al mundo sin interrumpir al Especialista.
        - El Secretario mata loops, timeouts y deltas muertos.
        - El Auditor destila soluciones limpias y solo sube oro al grafo maestro.
