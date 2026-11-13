// The software's name. The server is the source (branding.BRAND_NAME, sent in the boot data);
// the literal is used only on the screen shown when no boot data arrived at all.
// "Sidra" is the client company and comes from the server (boot.company), never from here.
export const PRODUCT_NAME = window.berjaya_boot?.product_name || 'Berjaya'
