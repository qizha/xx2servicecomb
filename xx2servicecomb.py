import os
import xml.etree.ElementTree as ET


class ReportItem:
  def __init__(self, loc, des, solution):
    self.Description = des
    self.Location = loc
    self.Solution = solution


def isSpringFile(f):
  if open(f).read().find("xmlns=\"http://www.springframework.org/schema/beans\"") == -1:
    return False
  else:
    return True
 
def scan_files(directory):
  file_dic={'pom':[], 'spring':[], 'java':[], 'others':[]}
    
  for root, sub_dirs, files in os.walk(directory):
    for special_file in files:
      if special_file=="pom.xml":
          file_dic['pom'].append(os.path.join(root,special_file))
          address_pom(os.path.join(root,special_file))
      elif special_file.endswith("java") or special_file.endswith("JAVA"):
        file_dic['java'].append(os.path.join(root,special_file))
      elif special_file.endswith("xml") or special_file.endswith("XML"):
        if isSpringFile(os.path.join(root,special_file)):
          file_dic['spring'].append(os.path.join(root,special_file))
        else:
          file_dic['others'].append(os.path.join(root,special_file))
      else:
        file_dic['others'].append(os.path.join(root,special_file))
               
  return file_dic

def address_pom(pomFile):
  report = {'changes':[], 'actions':[]}

  ET.register_namespace("xmlns:cse","http://www.huawei.com/schema/paas/cse/rpc")
  tree = ET.parse(pomFile)
  
  root = tree.getroot()
  print root.tag, root.attrib

  return report


if __name__ == '__main__':

  project_location = sys.argv[1]
  
  toPath = "/tmp"
  report = {'changes':[], 'action':[]}
  allfiles = scan_files(project_location)

  # Address pom files
  for pom in allfiles['pom']:
    r = address_pom(pom)
    report['changes'].extend(r['changes'])
    report['actions'].extend(r['actions'])
