from lims.models import SampleStatus, TestAssignment

def promote_samples_for_parameter_if_ready(parameter, client):
    """
    Promote all samples under this client to UNDER_REVIEW if all assignments
    for the given parameter are marked 'completed'.
    """
    samples = client.sample_set.all()
    assignments = TestAssignment.objects.filter(sample__in=samples, parameter=parameter)

    if all(a.status == "completed" for a in assignments):
        for s in samples:
            if s.status != SampleStatus.UNDER_REVIEW:
                s.status = SampleStatus.UNDER_REVIEW
                s.save(update_fields=["status"])
                print(f"✅ Promoted {s.sample_code} for {parameter.name}")
