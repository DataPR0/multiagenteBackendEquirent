INSERT INTO
    `tbl_usuarios_roles` (`rol_id`, `nombre_rol`)
VALUES
    (1, 'AGENT'),
    (2, 'SUPERVISOR'),
    (3, 'PRINCIPAL'),
    (4, 'ADMIN'),
    (5, 'SUPPORT'),
    (6, 'DATA_SECURITY'),
    (7, 'AUDIT');

INSERT INTO
    `tbl_usuarios_estados` (`estado_id`, `nombre_estado`)
VALUES
    (1, 'ONLINE'),
    (2, 'BREAK'),
    (3, 'OFFLINE'),
    (4, 'ALMUERZO'),
    (5, 'BAÑO');

INSERT INTO
    `tbl_conversaciones_estados` (`estado_id`, `nombre_estado`)
VALUES
    (1, 'PENDING'),
    (2, 'OPEN'),
    (3, 'CLOSED');

INSERT INTO
    `tbl_asignaciones_eventos` (`evento_id`, `nombre_evento`)
VALUES
    (1, 'ASSIGNED'),
    (2, 'TRANSFERRED'),
    (3, 'INTERVENTION');

INSERT INTO
    `tbl_usuarios_logs_eventos` (`evento_id`, `nombre_evento`)
VALUES
    (1, 'STATE_CHANGE'),
    (2, 'TRANSFER'),
    (3, 'END_CHAT');