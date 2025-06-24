from django.shortcuts import render
from lims.models import Sample, TestResult, ParameterGroup

def generate_coa(request, sample_batch_id):
    # Fetch all samples belonging to client with client_id=sample_batch_id
    samples = Sample.objects.filter(client__client_id=sample_batch_id)
    parameters = set()
    results = {}

    for sample in samples:
        # Assuming TestResult has foreign key 'assignment' that links to TestAssignment, 
        # which links to Sample and Parameter
        sample_results = TestResult.objects.filter(assignment__sample=sample)
        results[sample.sample_code] = {}
        for res in sample_results:
            param = res.assignment.parameter
            parameters.add(param)
            results[sample.sample_code][param.name] = res.result_value

    # Sort parameters by group name (assuming param.group.name exists)
    parameters = sorted(list(parameters), key=lambda p: p.group.name if p.group else "")

    return render(request, "lims/coa.html", {
        "samples": samples,
        "parameters": parameters,
        "results": results,
    })
