// Keep map tiles optional: a failed provider must not leave a grey form panel.
for (const doctype of ["Sidra Unit", "Sidra Construction Job"]) {
 frappe.ui.form.on(doctype, {
  setup(frm) { frm.set_df_property("sidra_location", "hidden", 1); },
  refresh(frm) {
   frm.add_custom_button(__("Show location map"), () => {
    frm.toggle_display("sidra_location", true);
    setTimeout(() => frm.fields_dict.sidra_location?.map?.invalidateSize(), 300);
    setTimeout(() => {
     const field = frm.fields_dict.sidra_location;
     const loaded = field?.$wrapper?.find(".leaflet-tile-loaded").length;
     if (!loaded) {
      frm.toggle_display("sidra_location", false);
      frappe.msgprint(__("Map tiles could not load. Your saved location has not changed. Use the staff location view or try again when the map provider is reachable."));
     }
    }, 8000);
   }, __("Location"));
  },
 });
}
