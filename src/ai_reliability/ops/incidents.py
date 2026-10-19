def incident_severity(service_down: bool, data_exposure: bool, major_degradation: bool) -> str:
    if data_exposure:
        return "SEV1"
    if service_down:
        return "SEV2"
    if major_degradation:
        return "SEV3"
    return "SEV4"
