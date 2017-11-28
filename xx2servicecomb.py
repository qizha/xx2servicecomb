#!/usr/bin/python

import os
import sys
import copy
import shutil
import xml.etree.ElementTree as ET

CSE_VERSION = '2.2.7'
ns = {
  'pom': 'http://maven.apache.org/POM/4.0.0',
  'spring': 'http://www.springframework.org/schema/beans',
  'dubbo': 'http://code.alibabatech.com/schema/dubbo',
  'cse': 'http://www.huawei.com/schema/paas/cse/rpc'
}

class Suggestion:
  def __init__(self, key, loc, des, solution):
    self.Key = key
    self.Description = des
    self.Location = loc
    self.Solution = solution

pre_defined_suggestion = {
  "parent_in_pom":Suggestion("parent_in_pom", "", "TBD", "TBD"),
  "project_structure":Suggestion("project_structure", "", "TBD", "TBD")
}

def prettyXml(element, indent, newline, level = 0):    
  if element is not None:   
      if element.text == None or element.text.isspace(): 
          element.text = newline + indent * (level + 1)      
      else:    
          element.text = newline + indent * (level + 1) + element.text.strip() + newline + indent * (level + 1)    
  temp = list(element) 
  for subelement in temp:    
      if temp.index(subelement) < (len(temp) - 1):    
          subelement.tail = newline + indent * (level + 1)    
      else:  
          subelement.tail = newline + indent * level    
      prettyXml(subelement, indent, newline, level = level + 1) 

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

def build_cse_dependency_management(parent):
  dependency = ET.SubElement(parent, '{%s}dependency' % ns['pom'])
  groupId = ET.SubElement(dependency, '{%s}groupId' % ns['pom'])
  groupId.text = "com.huawei.paas.cse"
  artifactId = ET.SubElement(dependency,'{%s}artifactId' % ns['pom'])
  artifactId.text = "cse-dependency"
  version = ET.SubElement(dependency,'{%s}:artifactId' % ns['pom'])
  version.text = CSE_VERSION
  typ = ET.SubElement(dependency,'{%s}type' % ns['pom'])
  typ.text = "pom"
  scope = ET.SubElement(dependency,'{%s}scope' % ns['pom'])
  scope.text = "import"
  return dependency

def build_cse_dependency(parent):
  # Build CSE element
  cse_dependency = ET.SubElement(parent, '{%s}dependency' % ns['pom'])
  cse_groupId = ET.SubElement(cse_dependency, '{%s}groupId' % ns['pom'])
  cse_groupId.text = "com.huawei.paas.cse"
  cse_artifactId = ET.SubElement(cse_dependency,'{%s}artifactId' % ns['pom'])
  cse_artifactId.text = "cse-solution-service-engine"
  # Build ServiceComb element
  sc_dependency = ET.SubElement(parent, '{%s}dependency' % ns['pom'])
  sc_groupId = ET.SubElement(sc_dependency, '{%s}groupId' % ns['pom'])
  sc_groupId.text = "io.servicecomb"
  sc_artifactId = ET.SubElement(sc_dependency,'{%s}artifactId' % ns['pom'])
  sc_artifactId.text = "provider-pojo"

def address_pom(context, project_root, target_path, pom_files):
  report = {'changes':[], 'suggestions':[]}

  # check parent setting
  for pom in pom_files:
    isChanged = False
    tree = ET.parse(pom) 
    root = tree.getroot()
    for parent in root.findall('pom:parent', ns):
      groupId = parent.find('pom:groupId', ns).text
      if groupId == "com.alibaba":
        s = copy.copy(pre_defined_suggestion['parent_in_pom'])
        s.Location = pom
        report['suggestions'].append(s)
    
    # Add dependencyManager in the parent
    if os.path.join(project_root, "pom.xml") == pom:
      dependency_management_position = 0
      properties_position = 0
      description_position = 0
      for index in range(len(root)):
        if root[index].tag == "{%s}%s" % (ns['pom'], "description"):
          description_position = index
        elif root[index].tag == "{%s}%s" % (ns['pom'], "properties"):
          properties_position = index
        elif root[index].tag == "{%s}%s" % (ns['pom'], "dependencyManagement"):
          dependency_management_position = index

      # insert dependency into DependencyManagement
      if dependency_management_position > 0:
        dependency_management = root[index]
        dependencies = dependency_management.find('pom:dependencies', ns)
        dep = build_cse_dependency_management(dependencies)
        dependencies.append(dep)
      else: # insert dependencyManagement in the suitable position
        dependency_management = ET.Element('{%s}dependencyManagement' % ns['pom'])
        dependencies = ET.SubElement(dependency_management,'{%s}dependencies' % ns['pom'])
        dep = build_cse_dependency_management(dependencies)
        dependencies.append(dep)
        if properties_position > 0:
          root.insert(properties_position + 1, dependency_management)
        elif description_position > 0:
          root.insert(description_position + 1, dependency_management)
        else:  #Append to pom file
          root.append(dependency_management)
      isChanged = True
    else: # Address children pom files
      dependencies = root.find('pom:dependencies', ns)
      if dependencies is not None:
        # 1. Remove alibaba dependencies
        for dependency in dependencies:
          artifactId = dependency.find('pom:artifactId', ns)
          if artifactId.text == "dubbo":
            dependencies.remove(dependency)
            isChanged = True
        # 2. Add CSE dependencies
        if isChanged:
          build_cse_dependency(dependencies)
        # 3. May need to remove the plugins used to assembly dubbo assembly files
        # TBD
        # 4. Need to setup CSE needed plugins, like maven-jar-plugin
        # TBD
  
    # Record to files
    if isChanged:
      target_file = os.path.join(target_path, project_root.split(os.sep)[-1] + "_servicecomb", pom[pom.find(project_root) + len(project_root) + 1:])
      if not os.path.isdir(os.path.split(target_file)[0]):
        os.mkdir(os.path.split(target_file)[0])
      prettyXml(root, '\t', '\n')
      report['changes'].append(target_file)
      tree.write(target_file, default_namespace=ns['pom'])

  return report

def address_spring(context, project_root, target_path, spring_files):
  report = {'changes':[], 'suggestions':[]}

  # check parent setting
  for spring in spring_files:
    # check if it is using dubbo in this file
    if open(spring).read().find("xmlns:dubbo=\"http://code.alibabatech.com/schema/dubbo\"") == -1:
      target_file = os.path.join(target_path, project_root.split(os.sep)[-1] + "_servicecomb", pom[pom.find(project_root) + len(project_root) + 1:])
      if not os.path.isdir(os.path.split(target_file)[0]):
        os.mkdir(os.path.split(target_file)[0])
      # Copy this file directly if it is not using dubbo  
      shutil.copyfile(spring, target_file)
    else: # Translate dubbo tags to CSE
      tree = ET.parse(spring) 
      root = tree.getroot()
      # Get application if there is
      application = root.find("./{%s}application" % ns['dubbo'])
      if application is not None:
        context['application_name'] = application
        root.remove(application)
      # Remove those un-needed elements
      removeables = root.findall("./{%s}*" % ns['dubbo'])
      print removeables

      for index in range(len(root)):
        if root[index].tag == "{%s}application" % ns['dubbo']:
          context['application_name'] = root[index].attrib['name']
          #root.remove(root[index])
        #elif root[index].tag == "{%s}registry" % ns['dubbo']:
          #root.remove(root[index])
        #elif root[index].tag == "{%s}protocol" % ns['dubbo']:
          #root.remove(root[index])
        elif root[index].tag == "{%s}service" % ns['dubbo']:
          beanId = root[index].attrib['ref']
          print beanId
          beans = root.findall("./{%s}bean[@id='%s']" % (ns['spring'], beanId))
          print beans

  print context
  return report


if __name__ == '__main__':

  project_location = sys.argv[1]
  output_location = sys.argv[2]
  
  context = {}
  report = {'changes':[], 'suggestions':[]}
  allfiles = scan_files(project_location)

  # Address Spring files
  r = address_spring(context, project_location, output_location, allfiles['spring'])
  report['changes'].extend(r['changes'])
  report['suggestions'].extend(r['suggestions'])
  # Address pom files
  r = address_pom(context, project_location, output_location, allfiles['pom'])
  report['changes'].extend(r['changes'])
  report['suggestions'].extend(r['suggestions'])

  for s in report['suggestions']:
    print s.Location
    print s.Description
    print s.Solution
    print "====================="
  for c in report['changes']:
    print c
