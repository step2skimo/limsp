

def calculate_nfe_and_me(results_dict):
    """
    results_dict: { 'Protein': 11.74, 'Fat': 1.40, 'Ash': 1.29, 'Moisture': 11.03, 'Fiber': 2.25 }
    Returns: NFE (%), ME (kcal/kg)
    """
    required = ['Protein', 'Fat', 'Ash', 'Moisture', 'Fiber']
    if not all(param in results_dict for param in required):
        return None, None

    protein = results_dict['Protein']
    fat = results_dict['Fat']
    ash = results_dict['Ash']
    moisture = results_dict['Moisture']
    fiber = results_dict['Fiber']

    nfe = round(100 - (protein + fat + ash + moisture + fiber), 2)
    me = round((protein * 4.0) + (nfe * 3.5) + (fat * 8.5), 0)

    return nfe, me
