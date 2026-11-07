// Serve this file from the ERPNext site. Do not put API secrets here.
// Claude should inject the authenticated request's CSRF token into the page/config.
window.SIDRA_CONFIG = window.SIDRA_CONFIG || {
 dashboardMethod: 'sidra_realestate.api.staff_dashboard.get_dashboard',
 locationsMethod: 'sidra_realestate.api.locations',
 // csrfToken: <server-rendered session CSRF token>,
 // mapsEmbedKey: <optional Google Maps Embed browser key restricted by HTTP referrer>
};
