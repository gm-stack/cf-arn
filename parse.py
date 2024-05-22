#!/usr/bin/env python3

import json
from collections import defaultdict

f = open("services.json", "r")
services = json.loads(f.read())
f.close()

resources = {}
for service_name, service_details in services.items():
    for resource_name, resource_details in service_details['resources'].items():
        resources[resource_name] = resource_details

resource_categories = defaultdict(list)


resource_attr_names = {}

for resource_name, resource_details in resources.items():
    resource_details = resource_details['details']

    attrs = resource_details.get("attrs", [])

    if 'Arn' in attrs:
        resource_categories['title_case_arn'].append(resource_name)
    elif 'ARN' in attrs:
        resource_categories['upper_case_arn'].append(resource_name)
    elif b := [a for a in attrs if a.endswith('Arn')]:
        resource_categories['title_case_arn_end'].append(resource_name)
        resource_attr_names[resource_name] = b
    elif b := [a for a in attrs if a.endswith('ARN')]:
        resource_categories['upper_case_arn_end'].append(resource_name)
        resource_attr_names[resource_name] = b
    elif attrs == []:
        resource_categories['no_attrs'].append(resource_name)
    else:
        resource_categories['other_attrs'].append(resource_name)

for resource_name, resource_list in resource_categories.items():
    print(f"{resource_name}: {len(resource_list)}")


resource_categories_ref = defaultdict(lambda: defaultdict(list))

for resource_category, resource_list in resource_categories.items():
    for resource_name in resource_list:
        resource_details = resources[resource_name]
        ref = resource_details['details'].get('Ref')
        if not ref:
            resource_categories_ref['no_ref'][resource_category].append(resource_name)
        elif 'Arn' in ref or 'ARN' in ref or 'Amazon Resource Name' in ref:
            resource_categories_ref['ref_is_arn'][resource_category].append(resource_name)
        elif 'name' in ref.lower():
            resource_categories_ref['ref_is_name'][resource_category].append(resource_name)
        elif ' id ' in ref.lower():
            resource_categories_ref['ref_is_id'][resource_category].append(resource_name)
        else:
            resource_categories_ref['ref_is_other'][resource_category].append(resource_name)

service_prefixes = set()
for resource_name in resources:
    prefix, suffix = resource_name.rsplit("::", 1)
    service_prefixes.add(prefix)

prefixes_by_category = {}
for ref_category, ref_items in resource_categories_ref.items():
    for attr_category, items in ref_items.items():
        resource_prefixes = set([n.rsplit("::", 1)[0] for n in items])
        prefixes_by_category[(ref_category, attr_category)] = resource_prefixes

unique_prefixes = set()
for service_prefix in service_prefixes:
    sp_map = [1 for c in prefixes_by_category.values() if service_prefix in c]
    if len(sp_map) == 1:
        unique_prefixes.add(service_prefix)


f = open("report.md",'w')

def write_list(service_list, arn_attr_label, ref_label):
    def format_service(prefix, service):
        full_name = f"{prefix}::{service}"
        resource_details = resources.get(full_name)
        resource_attr_name_list = resource_attr_names.get(full_name)

        resource_attrs = []
        if ref_label:
            resource_attrs.append(ref_label)
        if arn_attr_label:
            resource_attrs.append(arn_attr_label)
        if resource_attr_name_list:
            for resource_attr_name in resource_attr_name_list:
                resource_attrs.append(f"!GetAtt <Name>.{resource_attr_name}")

        if resource_attrs:
            resource_attr_str = "(" + ", ".join([f"`{r}`" for r in resource_attrs]) + ")"
        else:
            resource_attr_str = ""

        #if service != '*':
        return f"[`{prefix}::{service}`]({resource_details['url']}) {resource_attr_str}"
        #else:
        #    return f"`{prefix}::{service}`"

    services_to_write = set()
    for s in service_list:
        prefix = s.rsplit("::",1)[0]
        #if prefix in unique_prefixes:
        #    services_to_write.add(f"{prefix}::*")
        #else:
        services_to_write.add(s)

    services_dict = defaultdict(list)
    for s in services_to_write:
        p, sr = s.rsplit("::",1)
        services_dict[p].append(sr)

    output = ""
    for prefix in sorted(services_dict.keys()):
        services = sorted(services_dict[prefix])
        for service in services:
            output += f"* {format_service(prefix, service)}\n"
        #if len(services) == 1:
        #    output += f"* {format_service(prefix, services[0])}\n"
        #
        # else:
        #     output += "* "
        #     output += ", ".join([f"{format_service(prefix, service)}" for service in services])
        #     output += "\n"



    f.write(output)
    f.write("\n\n")

def write_header(heading):
    f.write(f"# {heading}\n\n")

def write_subheader(heading):
    f.write(f"## {heading}\n\n")

arn_attr_category_names = {
    'title_case_arn': '`!GetAtt <Name>.Arn` exists',
    'upper_case_arn': '`!GetAtt <Name>.ARN` exists',
    'title_case_arn_end': '`!GetAtt <Name>.<Thing>Arn` exists',
    'upper_case_arn_end': '`!GetAtt <Name>.<Thing>ARN` exists',
    'other_attrs': '`!GetAtt` has no ARN attribute',
    'no_attrs': '`!GetAtt` is unsupported'
}

ref_category_names = {
    'ref_is_arn': '`!Ref` is ARN',
    'ref_is_name': '`!Ref` is Name',
    'ref_is_id': '`!Ref` is ID',
    'ref_is_other': '`!Ref` is something else',
    'no_ref': '`!Ref` is unsupported'
}

arn_attr_category_labels = {
    'title_case_arn': '`!GetAtt <Name>.Arn`',
    'upper_case_arn': '`!GetAtt <Name>.ARN`',
    'title_case_arn_end': None,
    'upper_case_arn_end': None,
    'other_attrs': None,
    'no_attrs': None
}

ref_category_labels = {
    'ref_is_arn': '`!Ref`',
    'ref_is_name': None,
    'ref_is_id': None,
    'ref_is_other': None,
    'no_ref': None
}

f.write('# The big table of "How do I get an ARN?"\n')

f.write("| | " + " | ".join([f"{a}" for a in arn_attr_category_names.values()]) + " |\n")
f.write("| - | " + " | ".join([f" - " for a in arn_attr_category_names.values()]) + " |\n")

for ref_category, ref_category_name in ref_category_names.items():
    f.write(f"| {ref_category_name} |")

    for arn_attr_category, arn_attr_category_name in arn_attr_category_names.items():
        item_list = resource_categories_ref[ref_category][arn_attr_category]
        num = len(item_list)
        link_name = f"#{ref_category_name} and {arn_attr_category_name} - {len(item_list)} resources".replace(" ","-").replace("!","").replace("`","").replace("<","").replace(">","").replace(".","").lower()
        f.write(f" [{num}]({link_name}) | ")


    f.write("\n")

f.write("\n---\n")


for ref_category, ref_category_name in ref_category_names.items():
    for arn_attr_category, arn_attr_category_name in arn_attr_category_names.items():
        item_list = resource_categories_ref[ref_category][arn_attr_category]
        write_header(f"{ref_category_name} and {arn_attr_category_name} - {len(item_list)} resources")
        write_list(
            item_list,
            arn_attr_category_labels[arn_attr_category],
            ref_category_labels[ref_category]
        )

f.close()

#import code; code.interact(local=locals())

# attribute_names = set()
# for rsrc in resource_categories['other_attrs']:
#     attrs = resources[rsrc]['details'].get('attrs',[])
#     for attr in attrs:
#         attribute_names.add(attr)

# print(attribute_names)
