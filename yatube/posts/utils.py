from django.conf import settings
from django.core.paginator import Paginator


def get_pages(queryset, request):
    paginator = Paginator(queryset, settings.POSTS_PER_PAGE)
    # Из URL извлекаем номер запрошенной страницы
    page_number = request.GET.get('page')
    # Получаем набор записей для страницы с запрошенным номером
    page_obj = paginator.get_page(page_number)
    return{
        'paginator': paginator,
        'page_number': page_number,
        'page_obj': page_obj,
    }
