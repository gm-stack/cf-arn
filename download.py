#!/usr/bin/env python3

import re
import json

import requests
import urllib.parse
from bs4 import BeautifulSoup

service_list_pattern = re.compile(r'<a href="(.*)">(.*)<\/a>')
ref_description_pattern = re.compile(r'.* returns (?:the )?([\w\\\'\": \-()|/<>]*)[,.]')

start_page = "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html"


def get_and_parse_service_list(url):
    r = requests.get(url)
    service_html = r.text.split("<h6>Service resource type</h6>")[1].split("</div>")[0]
    return service_html.split("<li>")[1:]


services = get_and_parse_service_list(start_page)

service_details = {
    service_list_pattern.match(service)[2]: {
        'url': service_list_pattern.match(service)[1]
    }
    for service in services
}

def get_and_parse_resource_list(url):
    r = requests.get(url)
    service_html = r.text.split("<b>Resource types</b>")[1].split("</div>")[0]
    return service_html.split('<li class="listitem"><p>')[1:]


def parse_ref(ref):
    ref = ref.replace("\n", "").strip()
    ref = re.sub(r'\s+', ' ', ref)
    r = ref_description_pattern.search(ref)
    if r:
        return r[1]
    return ref


# some pages have the "ref" heading with nothing under it
# so next text is just the GetAtt heading, or something else
# also some have it and say it's not supported
bad_refs = (
    'Fn::GetAtt',
    'Examples',
    ''
)

def get_and_parse_resource_page(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')

    details = {}

    ref = soup.find('h3', string='Ref')
    if ref:
        ref_text = parse_ref(ref.next_sibling.text)
        if ref_text not in bad_refs:
            print(f"      Ref: {ref_text}")
            if ref_text:
                details['Ref'] = ref_text
                details['Ref_orig'] = ref.next_sibling.text

    attrs = {}
    getatt = soup.find('h3', string='Fn::GetAtt')
    if getatt:
        for s in getatt.next_siblings:
            if hasattr(s, 'find_all'):
                a = s.find_all("span", class_="term")
                for attr in a:
                    attrs[attr.text] = attr.parent.parent.find('p').text

        attr_names = list(attrs.keys())
        print(f"      GetAtt: {attr_names}")
        if attr_names:
            details['attrs'] = attr_names
    else:
        print("      GetAtt: None")

    return details


service_output = {}

for service_name, service_details in service_details.items():
    if service_name == "Shared property types":
        continue

    service_output[service_name] = {
        'details': service_details,
        'resources': {}
    }

    print(f"- {service_name}")
    service_url = urllib.parse.urljoin(start_page, service_details['url'])
    resources = get_and_parse_resource_list(service_url)

    resources = {
        service_list_pattern.match(resource)[2]:
        service_list_pattern.match(resource)[1]
        for resource in resources
    }

    for resource_name, resource_url in resources.items():
        print(f"  - {resource_name}")
        resource_url = urllib.parse.urljoin(service_url, resource_url)
        resource_details = get_and_parse_resource_page(resource_url)
        service_output[service_name]['resources'][resource_name] = {
            'url': resource_url,
            'details': resource_details
        }

f = open("services.json", 'w')
f.write(json.dumps(service_output))
f.close()
