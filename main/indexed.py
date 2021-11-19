from .exceptions import RefNotFoundError
from .models import RefData


RefDataManager = RefData.objects.db_manager('index')


def list_refs(dataset_id):
    return RefDataManager.filter(dataset__iexact=dataset_id)


def get_indexed_ref(dataset_id, ref, format='relaton'):
    """Retrieves citation from static indexed dataset.

    :param format string: "bibxml" or "relaton"
    :returns object: if format is "relaton", a dict.
    :returns string: if format is "bibxml", an XML string.
    :raises RefNotFoundError: either reference or requested format not found
    """

    if format not in ['relaton', 'bibxml']:
        raise ValueError("Unknown citation format requested")

    try:
        result = RefDataManager.get(
            ref__iexact=ref,
            dataset__iexact=dataset_id)
    except RefData.DoesNotExist:
        raise RefNotFoundError(
            "Cannot find requested reference in given dataset",
            ref)

    if format == 'relaton':
        return result.body

    else:
        bibxml_repr = result.representations.get('bibxml', None)
        if bibxml_repr:
            return bibxml_repr
        else:
            raise RefNotFoundError(
                "BibXML representation not found for requested reference",
                ref)
