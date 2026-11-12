from django.shortcuts import get_object_or_404, render

from tests.models import Article


def article(request, pk):
    return render(
        request, "article.html", {"article": get_object_or_404(Article, pk=pk)}
    )
