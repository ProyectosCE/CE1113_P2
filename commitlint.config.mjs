// Reglas de commits (Conventional Commits) para el CI: .github/workflows/ci.yml
// Formato: tipo(alcance opcional): descripción en español
//   feat(sd): agrega lectura de bloques de la microSD
//   fix(dsp): corrige la saturación del acumulador
//   docs: actualiza la guía de inicio
export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    // Tipos permitidos
    'type-enum': [2, 'always', [
      'feat', 'fix', 'docs', 'test', 'refactor', 'perf', 'build', 'ci', 'chore', 'style', 'revert',
    ]],
    // La descripción está en español: no forzar minúsculas ni otro estilo de mayúsculas
    'subject-case': [0],
    'header-max-length': [2, 'always', 100],
    // El cuerpo y el pie pueden tener líneas largas (rutas, logs): solo advertencia
    'body-max-line-length': [1, 'always', 100],
    'footer-max-line-length': [1, 'always', 100],
    // Alcances sugeridos (advertencia si se usa otro)
    'scope-enum': [1, 'always', [
      'hw', 'qsys', 'pines', 'hex', 'dsp', 'audio', 'adc', 'keys',
      'sw', 'drivers', 'sd', 'fat', 'wav', 'player', 'filtros', 'ui', 'volumen',
      'tests', 'scripts', 'ci', 'docs',
    ]],
  },
};
