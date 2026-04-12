"""
TMF DevKit — Seed data generator.

This is what separates tmf-mock from generic OpenAPI mockers.
Generates real telecom resource types: DSLAM, OLT, ONT, BTS with proper
network identifiers, realistic lifecycle states, and cross-API referential integrity.

Seed graph (bottom-up, matches real network architecture):
  Layer 0: Physical Resources (DSLAM, OLT, BTS)
  Layer 1: Logical Resources (DSL Ports, ONTs)
  Layer 2: Services (Broadband, Fiber, Mobile)
  Layer 3: ServiceOrders (provisioning history)
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from faker import Faker

fake = Faker()
rng = random.Random(42)

SERVICE_SPEC_NAMES = {
    "Broadband": "ADSL2+_Service_Spec",
    "VoIP": "SIP_Trunking_Spec",
    "IPTV": "IPTV_Multicast_Spec",
    "Mobile": "4G_LTE_Service_Spec",
    "LeasedLine": "EthernetPrivateLine_Spec",
}

RESOURCE_SPEC_NAMES = {
    "DSLAM": "Huawei_MA5800_Spec",
    "OLT": "Nokia_7360_ISAM_Spec",
    "BTS": "Ericsson_AIR6449_Spec",
    "DSL Port": "VDSL2_Port_Spec",
    "ONT": "Huawei_EG8145V5_Spec",
}

LOCATIONS = [
    ("Central Office - Pune", "Pune, MH"),
    ("Central Office - Mumbai", "Mumbai, MH"),
    ("Central Office - Delhi", "Delhi, DL"),
    ("Exchange - Andheri", "Andheri, Mumbai"),
    ("Exchange - Whitefield", "Whitefield, Bangalore"),
    ("Data Center - Chennai", "Chennai, TN"),
    ("PoP - Hyderabad", "Hyderabad, TS"),
]


def _uuid():
    return str(uuid.uuid4())


def _port_id(parent_id, slot, port):
    return f"{parent_id}/0/{slot}/{port}"


def _ont_serial():
    return "HWTC" + "".join(rng.choices("0123456789ABCDEF", k=8))


def _imsi():
    return f"404{rng.randint(10, 99)}{rng.randint(1000000000, 9999999999)}"


def _msisdn():
    return f"+91{rng.randint(7000000000, 9999999999)}"


def _ip_address():
    return f"10.{rng.randint(1, 254)}.{rng.randint(1, 254)}.{rng.randint(1, 254)}"


def _now():
    return datetime.now(tz=timezone.utc)


def _past(days=365):
    return _now() - timedelta(days=rng.randint(1, days))


def _future(days=180):
    return _now() + timedelta(days=rng.randint(1, days))


def _build_resource(name, category, resource_type, description, resource_status="available",
                    characteristics=None, location=None, spec_name=None):
    rid = _uuid()
    loc = location or rng.choice(LOCATIONS)
    spec_n = spec_name or RESOURCE_SPEC_NAMES.get(resource_type, f"{resource_type}_Spec")
    return {
        "id": rid,
        "href": f"http://localhost:8000/tmf-api/resourceInventoryManagement/v4/resource/{rid}",
        "@type": "Resource",
        "@baseType": "Resource",
        "name": name,
        "category": category,
        "description": description,
        "resourceStatus": resource_status,
        "administrativeState": "unlocked",
        "operationalState": "enable",
        "usageState": "active" if resource_status == "available" else "idle",
        "resourceVersion": f"1.{rng.randint(0, 5)}",
        "startOperatingDate": _past(730).isoformat(),
        "resourceSpecification": {"id": _uuid(), "name": spec_n, "version": "4.0"},
        "resourceCharacteristic": characteristics or [],
        "place": [{"id": _uuid(), "name": loc[0], "role": "location", "@referredType": "GeographicSite"}],
        "relatedParty": [{"id": _uuid(), "name": "Network Operations", "role": "owner", "@referredType": "Organization"}],
    }


def generate_resources(base_url="http://localhost:8000"):
    resources = []
    co = rng.choice(LOCATIONS)

    # 3 DSLAMs + 12 DSL ports each
    for i in range(1, 4):
        dslam_name = f"DSLAM-{co[0].replace(' ', '-')}-{i:02d}"
        vendor = rng.choice(["Huawei", "Nokia", "ADTRAN"])
        dslam = _build_resource(
            name=dslam_name, category="Physical", resource_type="DSLAM",
            description=f"VDSL2/ADSL2+ access multiplexer at {co[0]}",
            characteristics=[
                {"name": "vendor", "value": vendor, "valueType": "string"},
                {"name": "model", "value": "MA5800-X17" if vendor == "Huawei" else "7302 ISAM", "valueType": "string"},
                {"name": "slot_count", "value": 17, "valueType": "integer"},
                {"name": "max_ports", "value": 384, "valueType": "integer"},
                {"name": "uplink_capacity_gbps", "value": 100, "valueType": "integer"},
                {"name": "ip_address", "value": _ip_address(), "valueType": "string"},
            ],
        )
        resources.append(dslam)

        for slot in range(0, 3):
            for port in range(0, 4):
                port_name = _port_id(dslam_name, slot, port)
                status = rng.choices(["available", "reserved", "standby"], weights=[0.6, 0.3, 0.1])[0]
                dsl_port = _build_resource(
                    name=port_name, category="Logical", resource_type="DSL Port",
                    description=f"VDSL2 port on {dslam_name}", resource_status=status,
                    characteristics=[
                        {"name": "line_rate_down_mbps", "value": rng.choice([20, 40, 80, 100]), "valueType": "integer"},
                        {"name": "line_rate_up_mbps", "value": rng.choice([5, 10, 20, 40]), "valueType": "integer"},
                        {"name": "snr_margin_db", "value": round(rng.uniform(6.0, 20.0), 1), "valueType": "float"},
                        {"name": "attenuation_db", "value": round(rng.uniform(5.0, 40.0), 1), "valueType": "float"},
                        {"name": "parent_resource_id", "value": dslam["id"], "valueType": "string"},
                    ],
                )
                resources.append(dsl_port)

    # OLT
    olt_name = f"OLT-{co[0].replace(' ', '-')}-01"
    olt = _build_resource(
        name=olt_name, category="Physical", resource_type="OLT",
        description=f"XGS-PON OLT at {co[0]}",
        characteristics=[
            {"name": "vendor", "value": "Nokia", "valueType": "string"},
            {"name": "model", "value": "7360 ISAM FX", "valueType": "string"},
            {"name": "pon_ports", "value": 16, "valueType": "integer"},
            {"name": "max_onts", "value": 512, "valueType": "integer"},
            {"name": "ip_address", "value": _ip_address(), "valueType": "string"},
        ],
    )
    resources.append(olt)

    # 5 ONTs
    for i in range(1, 6):
        ont_serial = _ont_serial()
        ont = _build_resource(
            name=f"ONT-{ont_serial}", category="Physical", resource_type="ONT",
            description="XGS-PON ONT at subscriber premises",
            resource_status=rng.choice(["available", "reserved"]),
            characteristics=[
                {"name": "serial_number", "value": ont_serial, "valueType": "string"},
                {"name": "vendor", "value": "Huawei", "valueType": "string"},
                {"name": "model", "value": "EG8145V5", "valueType": "string"},
                {"name": "gpon_speed_gbps", "value": 10, "valueType": "integer"},
                {"name": "parent_olt_id", "value": olt["id"], "valueType": "string"},
                {"name": "pon_port", "value": f"0/0/{i}", "valueType": "string"},
            ],
            spec_name="Huawei_EG8145V5_Spec",
        )
        resources.append(ont)

    # BTS
    bts_name = f"BTS-{fake.city().replace(' ', '-')}-{rng.randint(1, 50):03d}"
    bts = _build_resource(
        name=bts_name, category="Physical", resource_type="BTS",
        description="4G/5G NR Base Transceiver Station",
        characteristics=[
            {"name": "vendor", "value": "Ericsson", "valueType": "string"},
            {"name": "model", "value": "AIR 6449", "valueType": "string"},
            {"name": "bands", "value": "B3,B7,B28,N78", "valueType": "string"},
            {"name": "latitude", "value": round(fake.latitude(), 6), "valueType": "float"},
            {"name": "longitude", "value": round(fake.longitude(), 6), "valueType": "float"},
            {"name": "cell_count", "value": 3, "valueType": "integer"},
        ],
    )
    resources.append(bts)
    return resources


def generate_services(resources, base_url="http://localhost:8000"):
    services = []
    reserved_ports = [r for r in resources if r.get("category") == "Logical" and r.get("resourceStatus") == "reserved"]
    ont_sample = [r for r in resources if "ONT" in r.get("name", "")]

    for port in reserved_ports[:5]:
        svc_id = _uuid()
        msisdn = _msisdn()
        service = {
            "id": svc_id,
            "href": f"{base_url}/tmf-api/serviceInventoryManagement/v4/service/{svc_id}",
            "@type": "Service", "@baseType": "Service",
            "name": f"Broadband-{msisdn[-8:]}",
            "description": "VDSL2 Broadband service",
            "serviceType": "Broadband", "category": "Fixed",
            "state": rng.choices(["active", "inactive", "reserved"], weights=[0.7, 0.15, 0.15])[0],
            "startDate": _past(400).isoformat(),
            "hasStarted": True, "isStateful": True,
            "serviceSpecification": {"id": _uuid(), "name": SERVICE_SPEC_NAMES["Broadband"], "version": "3.0"},
            "serviceCharacteristic": [
                {"name": "downloadSpeed_Mbps", "value": port.get("resourceCharacteristic", [{}])[0].get("value", 80), "valueType": "integer"},
                {"name": "uploadSpeed_Mbps", "value": 20, "valueType": "integer"},
                {"name": "technology", "value": "VDSL2", "valueType": "string"},
                {"name": "msisdn", "value": msisdn, "valueType": "string"},
                {"name": "ipAddress", "value": _ip_address(), "valueType": "string"},
            ],
            "supportingResource": [{"id": port["id"], "href": port["href"], "name": port["name"], "role": "access_port", "@referredType": "Resource"}],
            "relatedParty": [{"id": _uuid(), "name": fake.name(), "role": "subscriber", "@referredType": "Individual"}],
        }
        services.append(service)

    for ont in ont_sample[:3]:
        svc_id = _uuid()
        service = {
            "id": svc_id,
            "href": f"{base_url}/tmf-api/serviceInventoryManagement/v4/service/{svc_id}",
            "@type": "Service", "@baseType": "Service",
            "name": f"FiberBB-{ont['name'].split('-')[-1][:6]}",
            "description": "XGS-PON Fiber Broadband service",
            "serviceType": "Broadband", "category": "Fixed", "state": "active",
            "startDate": _past(200).isoformat(), "hasStarted": True, "isStateful": True,
            "serviceSpecification": {"id": _uuid(), "name": "XGS-PON_Broadband_Spec", "version": "1.0"},
            "serviceCharacteristic": [
                {"name": "downloadSpeed_Mbps", "value": 1000, "valueType": "integer"},
                {"name": "uploadSpeed_Mbps", "value": 1000, "valueType": "integer"},
                {"name": "technology", "value": "XGS-PON", "valueType": "string"},
            ],
            "supportingResource": [{"id": ont["id"], "href": ont["href"], "name": ont["name"], "role": "cpe", "@referredType": "Resource"}],
            "relatedParty": [{"id": _uuid(), "name": fake.name(), "role": "subscriber", "@referredType": "Individual"}],
        }
        services.append(service)

    bts_resources = [r for r in resources if "BTS" in r.get("name", "")]
    if bts_resources:
        bts = bts_resources[0]
        svc_id = _uuid()
        service = {
            "id": svc_id,
            "href": f"{base_url}/tmf-api/serviceInventoryManagement/v4/service/{svc_id}",
            "@type": "Service", "@baseType": "Service",
            "name": f"MobileSvc-{_imsi()[-6:]}",
            "description": "4G LTE Mobile Data Service",
            "serviceType": "Mobile", "category": "Mobile", "state": "active",
            "startDate": _past(300).isoformat(), "hasStarted": True, "isStateful": True,
            "serviceSpecification": {"id": _uuid(), "name": SERVICE_SPEC_NAMES["Mobile"], "version": "2.0"},
            "serviceCharacteristic": [
                {"name": "imsi", "value": _imsi(), "valueType": "string"},
                {"name": "msisdn", "value": _msisdn(), "valueType": "string"},
                {"name": "apn", "value": "internet.operator.com", "valueType": "string"},
                {"name": "qos_profile", "value": "Gold", "valueType": "string"},
            ],
            "supportingResource": [{"id": bts["id"], "href": bts["href"], "name": bts["name"], "role": "serving_bts", "@referredType": "Resource"}],
            "relatedParty": [{"id": _uuid(), "name": fake.name(), "role": "subscriber", "@referredType": "Individual"}],
        }
        services.append(service)

    return services


def generate_service_orders(services, base_url="http://localhost:8000"):
    orders = []
    for svc in services[:4]:
        order_id = _uuid()
        order_date = _past(400)
        completion_date = order_date + timedelta(hours=rng.randint(1, 48))
        subscriber = (svc.get("relatedParty") or [{}])[0]
        order = {
            "id": order_id,
            "href": f"{base_url}/tmf-api/serviceOrdering/v4/serviceOrder/{order_id}",
            "@type": "ServiceOrder", "@baseType": "ServiceOrder",
            "description": f"Provision {svc['serviceType']} service for {subscriber.get('name', 'Subscriber')}",
            "category": svc.get("category", "Fixed"),
            "priority": rng.choice(["1", "2", "3", "4"]),
            "state": "completed",
            "orderDate": order_date.isoformat(),
            "completionDate": completion_date.isoformat(),
            "requestedStartDate": order_date.isoformat(),
            "requestedCompletionDate": (order_date + timedelta(days=3)).isoformat(),
            "relatedParty": svc.get("relatedParty", []),
            "orderItem": [{"id": "1", "action": "add", "state": "completed", "quantity": 1,
                           "service": {"id": svc["id"], "href": svc["href"], "name": svc["name"],
                                       "serviceType": svc.get("serviceType"), "state": svc.get("state"), "@type": "Service"}}],
        }
        orders.append(order)

    pending_id = _uuid()
    orders.append({
        "id": pending_id,
        "href": f"{base_url}/tmf-api/serviceOrdering/v4/serviceOrder/{pending_id}",
        "@type": "ServiceOrder", "@baseType": "ServiceOrder",
        "description": "New Broadband activation — pending provisioning",
        "category": "Fixed", "priority": "2", "state": "inProgress",
        "orderDate": _past(2).isoformat(),
        "requestedStartDate": _past(2).isoformat(),
        "requestedCompletionDate": _future(3).isoformat(),
        "relatedParty": [{"id": _uuid(), "name": fake.name(), "role": "subscriber", "@referredType": "Individual"}],
        "orderItem": [{"id": "1", "action": "add", "state": "inProgress", "quantity": 1,
                       "service": {"name": "New-Broadband-Pending", "serviceType": "Broadband", "state": "designed",
                                   "serviceCharacteristic": [{"name": "downloadSpeed_Mbps", "value": 100, "valueType": "integer"},
                                                              {"name": "technology", "value": "VDSL2", "valueType": "string"}],
                                   "@type": "Service"}}],
    })
    return orders


def seed_store(store, base_url="http://localhost:8000") -> dict:
    rng.seed(42)
    resources = generate_resources(base_url)
    for r in resources:
        store.create_resource(r)
    services = generate_services(resources, base_url)
    for s in services:
        store.create_service(s)
    orders = generate_service_orders(services, base_url)
    for o in orders:
        store.create_service_order(o)
    return {"seeded": {"resources": len(resources), "services": len(services), "serviceOrders": len(orders)}}
