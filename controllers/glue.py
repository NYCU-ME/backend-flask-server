import re
import ipaddress
from flask import request, g

from main import app, authService, dnsService
from services import Operation


domain_regex = re.compile(
    r'^([A-Za-z0-9]\.|[A-Za-z0-9][A-Za-z0-9-]{0,61}[A-Za-z0-9]\.){1,3}[A-Za-z]{2,6}$'
)

def is_ip(addr, protocol=ipaddress.IPv4Address):
    try:
        ip = ipaddress.ip_address(addr)
        return str(ip) if isinstance(ip, protocol) else False
    except Exception:
        return False

def is_domain(domain):
    return domain_regex.fullmatch(domain)

def check_type(type_, value):

    if type_ not in {'A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS'}:
        return {
            "errorType": "DNSError",
            "msg": f"Not allowed type {type_}."
        }, 403
    if type_ == 'A':
        if not is_ip(value, ipaddress.IPv4Address):
            return {
                "errorType": "DNSError",
                "msg": "Type A with non-IPv4 value."
            }, 403

        value = is_ip(value, ipaddress.IPv4Address)

    if type_ == 'AAAA':
        if not is_ip(value, ipaddress.IPv6Address):
            return {
                "errorType": "DNSError",
                "msg": "Type AAAA with non-IPv6 value."
            }, 403

        value = is_ip(value, ipaddress.IPv6Address)

    if type_ == 'CNAME' and not is_domain(value):
        return {
            "errorType": "DNSError",
            "msg": "Type CNAME with non-domain-name value."
        }, 403

    if type_ == 'MX' and not is_domain(value):
        return {
            "errorType": "DNSError",
            "msg": "Type MX with non-domain-name value."
        }, 403

    if type_ == 'TXT' and (len(value) > 255 or value.count('\n')):
        return {
            "errorType": "DNSError", 
            "msg": "Type TXT with value longer than 255 chars or more than 1 line."
        }, 403


    if type_ == 'NS' and not is_domain(value):
        return {"errorType": "DNSError", "msg": "Type NS with non-domain-name value."}, 403

    return None

@app.route("/glue/<path:domain>/records/<string:subdomain>/<string:type_>/<string:value>", methods=['POST'])
def add_glue_record(domain, subdomain, type_, value):
    if not g.user:
        return {"msg": "Unauth."}, 401

    domain_struct = domain.lower().strip('/').split('/')
    domain_name   = '.'.join(reversed(domain_struct))

    check_result = check_type(type_, value)
    if check_result:
        return check_result

    try:
        authService.authorize_action(g.user['uid'], Operation.MODIFY, domain_name)
        dnsService.add_glue_record(domain_name, subdomain, type_, value)
        return {"msg": "ok"}
    except Exception as e:
        return {"msg": str(e)}, 403

@app.route("/glue/<path:domain>/records/<string:subdomain>/<string:type_>/<string:value>", methods=['DELETE'])
def del_glue_record(domain, subdomain, type_, value):
    if not g.user:
        return {"msg": "Unauth."}, 401

    domain_struct = domain.lower().strip('/').split('/')
    domain_name   = '.'.join(reversed(domain_struct))

    check_result = check_type(type_, value)
    if check_result:
        return check_result

    try:
        authService.authorize_action(g.user['uid'], Operation.MODIFY, domain_name)
        dnsService.del_glue_record(domain_name, subdomain, type_, value)
        return {"msg": "ok"}
    except Exception as e:
        return {"msg": str(e)}, 403