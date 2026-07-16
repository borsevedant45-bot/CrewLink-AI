import '@testing-library/jest-dom';
import i18n from 'i18next';
import ICU from 'i18next-icu';
import { initReactI18next } from 'react-i18next';

void i18n.use(ICU).use(initReactI18next).init({
  resources: {
    en: {
      translation: {
        app: { title: 'CrewLink AI', loading: 'Loading...', error: 'Something went wrong', retry: 'Retry', offline: 'Offline' },
        nav: { tasks: 'Tasks', chat: 'Chat', ask: 'Ask CrewLink', supervisor: 'Supervisor', settings: 'Settings', logout: 'Log Out' },
        auth: { login: 'Log In', badgeCode: 'Badge Code', pin: 'PIN', loginError: 'Invalid credentials', sessionExpired: 'Session expired' },
        task: { feed: 'Task Feed', empty: 'No tasks', newTasks: '{count} new tasks', highestPriority: 'Highest: {priority}', ariaNewTask: 'New: {category}, {zone}, {priority}' },
        incident: { detail: 'Incident Detail', category: 'Category', location: 'Location', description: 'Description', source: 'Source', actions: 'Actions', acknowledge: 'Acknowledge', enRoute: 'En Route', resolve: 'Resolve', escalate: 'Escalate', confirmEscalate: 'Confirm?', notes: 'Notes', notesPlaceholder: 'Describe...', notesRequired: 'Required', sessionExpired: 'Session expired', reauth: 'Log in again', routeTitle: 'Route', routeBody: 'From {zone}' },
        chat: { title: 'Chat Bridge', inputPlaceholder: 'Type...', send: 'Send', translating: 'Translating...', detectedLanguage: 'Detected: {language}', wrongLanguage: 'Wrong?', sessionClosed: 'Closed', noSession: 'No session', noMessages: 'No messages', messages: 'Messages', confidenceMedium: 'Moderate confidence', confidenceLow: 'Low confidence', fallbackUsed: 'Translation unavailable', requestInterpreter: 'Request human interpreter', requesting: 'Requesting...' },
        ask: { title: 'Ask CrewLink', placeholder: 'Ask...', searching: 'Searching...', noResults: 'Not found', error: 'Failed', voiceInput: 'Voice', voiceDisabled: 'Not available (Key Assumption 3)', fallbackNextStep: 'Please confirm with a supervisor.', fallbackBadge: 'Unverified', history: 'History' },
        supervisor: { title: 'Supervisor Dashboard', incidents: 'Incidents', zones: 'Zones', volunteers: 'Volunteers', openIncidents: 'Open Incidents', totalVolunteers: 'Total Volunteers', available: 'Available', density: 'Crowd Density', crowdHigh: 'High', loading: 'Loading...', error: 'Error', venueTotal: 'Venue-wide: {count}' },
        source: { simulated: 'Simulated', volunteer: 'Volunteer Reported', supervisor: 'Supervisor Created' },
        priority: { urgent: 'Urgent', moderate: 'Moderate', low: 'Low' },
        theme: { light: 'Light', dark: 'Dark', toggle: 'Toggle theme' },
        common: { back: 'Back', close: 'Close', confirm: 'Confirm', cancel: 'Cancel', save: 'Save', delete: 'Delete' },
        status: { reported: 'Reported', triaged: 'Triaged', dispatched: 'Dispatched', acknowledged: 'Acknowledged', enRoute: 'En Route', inProgress: 'In Progress', resolved: 'Resolved', cancelled: 'Cancelled', escalated: 'Escalated' },
      },
    },
    es: {
      translation: {
        app: { title: 'CrewLink AI', loading: 'Cargando...', error: 'Algo salió mal', retry: 'Reintentar', offline: 'Desconectado' },
        nav: { tasks: 'Tareas', chat: 'Chat', ask: 'Preguntar a CrewLink', supervisor: 'Supervisor', settings: 'Ajustes', logout: 'Cerrar sesión' },
        auth: { login: 'Iniciar sesión', badgeCode: 'Código', pin: 'PIN', loginError: 'Credenciales inválidas', sessionExpired: 'Sesión expirada' },
        task: { feed: 'Tareas', empty: 'Sin tareas', newTasks: '{count} tareas nuevas', highestPriority: 'Máxima: {priority}', ariaNewTask: 'Nueva: {category}, {zone}, {priority}' },
        incident: { detail: 'Detalle', category: 'Categoría', location: 'Ubicación', description: 'Descripción', source: 'Fuente', actions: 'Acciones', acknowledge: 'Confirmar', resolve: 'Resolver', escalate: 'Escalar', confirmEscalate: '¿Confirmar?', notes: 'Notas', notesRequired: 'Obligatorio' },
        chat: { title: 'Chat', inputPlaceholder: 'Escribe...', send: 'Enviar', translating: 'Traduciendo...', detectedLanguage: 'Detectado: {language}', wrongLanguage: '¿Incorrecto?', sessionClosed: 'Cerrado' },
        ask: { title: 'Preguntar', placeholder: 'Pregunta...', searching: 'Buscando...', noResults: 'No encontrado', error: 'Error' },
        supervisor: { title: 'Panel', incidents: 'Incidentes', zones: 'Zonas', volunteers: 'Voluntarios' },
        source: { simulated: 'Simulado', volunteer: 'Reportado', supervisor: 'Creado' },
        priority: { urgent: 'Urgente', moderate: 'Moderado', low: 'Baja' },
        theme: { light: 'Claro', dark: 'Oscuro', toggle: 'Cambiar tema' },
        common: { back: 'Atrás', close: 'Cerrar', confirm: 'Confirmar', cancel: 'Cancelar', save: 'Guardar', delete: 'Eliminar' },
        status: { reported: 'Reportado', triaged: 'Clasificado', dispatched: 'Despachado', acknowledged: 'Confirmado', enRoute: 'En camino', inProgress: 'En progreso', resolved: 'Resuelto', cancelled: 'Cancelado', escalated: 'Escalado' },
      },
    },
  },
  lng: 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  returnObjects: true,
});
