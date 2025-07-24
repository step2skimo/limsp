def split_samples_by_accreditation(samples):
    accredited_groups = {"Gross Energy", "Vitamins & Contaminants", "Aflatoxin", "CHO", "ME", "Fiber"}
    accredited_samples = []
    unaccredited_samples = []

    for sample in samples:
        sample_groups = {
            ta.parameter.group.name if ta.parameter.group else ""
            for ta in sample.testassignment_set.all()
        }
        if sample_groups and sample_groups.issubset(accredited_groups):
            accredited_samples.append(sample)
        else:
            unaccredited_samples.append(sample)

    return accredited_samples, unaccredited_samples
