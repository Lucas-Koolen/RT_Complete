def determine_rotation_sequence(detected_box, target_box):
    """
    Berekent de rotaties die nodig zijn om de gedetecteerde box
    in de gewenste oriëntatie (zoals in de database) te krijgen.
    Nu nog een placeholder: geeft altijd één FWD-rotatie op servo 1.

    Parameters:
        detected_box (dict): {'length': .., 'width': .., 'height': ..}
        target_box (dict): uit database

    Returns:
        List[str]: lijst van commando's zoals ['ROTATE 1 FWD', 'ROTATE 2 REV']
    """
    # TODO: implementeer echte oriëntatievergelijking op basis van vorm/positie
    return ['ROTATE 1 FWD']
