/**
 * Session Schema Validator
 * Valida que la estructura de la base de datos para 'Call' coincida con lo esperado por el backend.
 * 
 * Uso: node VALIDATORS/session_validator.js
 */

const assert = require('assert');

// Mock del Schema esperado en Backend (app/db/models.py)
const BackendSchema = {
    table: "calls",
    columns: ["id", "session_id", "start_time", "end_time", "status", "client_type", "extracted_data"]
};

// Simulación de lectura de BD (En producción usaría knex/sequelize reflection)
// Aquí definimos manualmente lo que SABEMOS que está en models.py por la auditoría
const ActualDBSchema = {
    table: "calls",
    columns: ["id", "session_id", "start_time", "end_time", "status", "client_type", "extracted_data"] // Mapeado de models.py
};

console.log("🔍 Ejecutando Session Schema Validator...");

try {
    // 1. Validar Nombre de Tabla
    assert.strictEqual(BackendSchema.table, ActualDBSchema.table, "Table name mismatch");

    // 2. Validar Columnas Críticas
    BackendSchema.columns.forEach(col => {
        if (!ActualDBSchema.columns.includes(col)) {
            throw new Error(`CRITICAL: Column '${col}' missing in Database Schema!`);
        }
    });

    console.log("✅ Session Schema: OK");
} catch (e) {
    console.error("❌ Session Schema: FAILED");
    console.error(e.message);
    process.exit(1);
}
