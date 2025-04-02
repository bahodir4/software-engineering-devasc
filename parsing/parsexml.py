import xml.etree.ElementTree as ET
import re

xml = ET.parse("myfile_12214739.xml")
root = xml.getroot()

ns = re.match('{.*}', root.tag).group(0)
editconf = root.find("{}edit-config".format(ns))
defop = editconf.find("{}default-operation".format(ns))
testop = editconf.find("{}test-option".format(ns))

print("The default-operation contains: {}".format(defop.text))
print("The test-option contains: {}".format(testop.text))
