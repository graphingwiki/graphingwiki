# -*- coding: utf-8 -*-

def macro_StressReport(macro):
    return '''
<form action="?action=stressreport" method="POST">
  <table border="1" align="center">
  <tr align="center">
    <td>No or low activity</td>
    <td>Some activity</td>
    <td>High activity</td>
  </tr>
  <tr align="center">
    <td><input type="submit" name="stress_0_0" value="In control"></input></td>
    <td><input type="submit" name="stress_0_1" value="In control"></input></td>
    <td><input type="submit" name="stress_0_2" value="In control"></input></td>
  </tr>
  <tr align="center">
    <td><input type="submit" name="stress_1_0" value="No control"></input></td>
    <td><input type="submit" name="stress_1_1" value="No control"></input></td>
    <td><input type="submit" name="stress_1_2" value="No control"></input></td>
  </tr>
  </table>
</form>
<br>'''
