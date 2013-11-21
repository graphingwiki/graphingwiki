# -*- coding: utf-8 -*-

def macro_Timestamper(macro):
    return '''
<form action="?action=timestamper" method="POST">
  <input type="submit" value="Timestamp"></input>
  <input type="hidden" name="meta_key", value="Timestamp"></input>
</form>
<br>'''
