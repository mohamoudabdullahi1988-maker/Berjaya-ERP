"""Unit checks of the adapter's permission and update boundary; no Frappe runtime claimed."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
ROOT=Path(__file__).parents[1]/'integration/frappe/sidra_realestate/api'
class Denied(Exception):pass
class Stale(Exception):pass
class Meta:
 def has_field(self,name):return name=='sidra_location'
class Doc:
 def __init__(self,allowed=True):
  self.doctype='Sidra Construction Job';self.name='DEMO-001';self.modified='2026-11-07 10:00:00';self.docstatus=0;self.meta=Meta();self.allowed=allowed;self.values={'gps':'9.5, 44'};self.writes=[]
 def check_permission(self,p):
  if not self.allowed:raise Denied()
 def has_permission(self,p):return self.allowed
 def get(self,k):return self.values.get(k)
 def db_set(self,k,v):self.writes.append((k,v));self.values[k]=v
 def add_comment(self,*args):pass
 def notify_update(self):pass
class APIBoundary(unittest.TestCase):
 def setUp(self):
  self.doc=Doc()
  self.frappe=types.ModuleType('frappe');self.frappe.whitelist=lambda **kw:lambda f:f;self.frappe._=lambda v:v;self.frappe.PermissionError=Denied;self.frappe.TimestampMismatchError=Stale
  self.frappe.get_doc=lambda *a,**kw:self.doc
  def throw(message,exc=ValueError):raise exc(message)
  self.frappe.throw=throw
  utils=types.ModuleType('frappe.utils');utils.get_datetime=lambda v:datetime.fromisoformat(str(v))
  package=types.ModuleType('sidra_test_api');package.__path__=[str(ROOT)]
  self.modules=patch.dict(sys.modules,{'frappe':self.frappe,'frappe.utils':utils,'sidra_test_api':package});self.modules.start();self.addCleanup(self.modules.stop)
  for name in ('location_geometry','locations'):
   spec=importlib.util.spec_from_file_location('sidra_test_api.'+name,ROOT/(name+'.py'));module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
  self.api=sys.modules['sidra_test_api.locations']
 def test_arbitrary_doctype_is_refused(self):
  with self.assertRaises(Denied):self.api.get_location('User','Administrator')
 def test_no_read_permission_does_not_return_coordinates(self):
  self.doc.allowed=False
  with self.assertRaises(Denied):self.api.get_location(self.doc.doctype,self.doc.name)
 def test_no_write_permission_changes_nothing(self):
  self.doc.allowed=False
  with self.assertRaises(Denied):self.api.set_location(self.doc.doctype,self.doc.name,9,44,self.doc.modified)
  self.assertEqual(self.doc.writes,[])
 def test_stale_edit_is_refused_before_write(self):
  with self.assertRaises(Stale):self.api.set_location(self.doc.doctype,self.doc.name,9,44,'2026-11-06 10:00:00')
  self.assertEqual(self.doc.writes,[])
 def test_only_pin_changes_and_legacy_gps_is_preserved(self):
  result=self.api.set_location(self.doc.doctype,self.doc.name,9.6,44.1,self.doc.modified)
  self.assertEqual([k for k,v in self.doc.writes],['sidra_location']);self.assertEqual(self.doc.values['gps'],'9.5, 44');self.assertEqual(result['latitude'],9.6)
 def test_existing_polygon_is_preserved(self):
  self.doc.values['sidra_location']='{"type":"Polygon","coordinates":[]}'
  with self.assertRaises(ValueError):self.api.set_location(self.doc.doctype,self.doc.name,9,44,self.doc.modified)
  self.assertEqual(self.doc.writes,[])
 def test_submitted_record_is_not_changed(self):
  self.doc.docstatus=1
  with self.assertRaises(ValueError):self.api.set_location(self.doc.doctype,self.doc.name,9,44,self.doc.modified)
  self.assertEqual(self.doc.writes,[])
if __name__=='__main__':unittest.main()
