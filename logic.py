import os
import uuid
import shutil
import codecs

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.template.loader import render_to_string

from core import files, models as core_models
from journal import models
from submission import models as submission_models


def file_path(article_id, uuid_filename):
    return os.path.join(
        settings.BASE_DIR,
        'files',
        'articles',
        str(article_id),
        str(uuid_filename),
    )

def generate_jats_metadata(request, article, article_folder):
    print('Generating JATS file...')
    template = 'portico/jats.xml'
    context = {
        'article': article,
        'journal': request.journal
    }

    rendered_jats = render_to_string(template, context)
    file_name = '{id}.xml'.format(id=article.pk)
    full_path = os.path.join(article_folder, file_name)

    with codecs.open(full_path, 'w', "utf-8") as file:
        file.write(rendered_jats)
        file.close()


def prepare_temp_folder(request, issue=None, article=None):
    """
    Perpares a temp folder to store files for zipping
    :param issue: Issue Object
    :param article: Article object
    :return: Folder path, string
    """
    folder_string = str(uuid.uuid4())

    if article and issue:
        folder_string = '{journal_code}_{vol}_{issue}_{pk}'.format(
            journal_code=request.journal.code,
            vol=issue.volume,
            issue=issue.issue,
            pk=article.pk)
    elif issue:
        folder_string = '{journal_code}_{vol}_{issue}_{year}'.format(
            journal_code=request.journal.code,
            vol=issue.volume,
            issue=issue.issue,
            year=issue.date.year)

    folder = os.path.join(settings.BASE_DIR, 'files', 'temp', 'portico', folder_string)
    files.mkdirs(folder)

    return folder, folder_string


def zip_portico_folder(temp_folder):
    shutil.make_archive(temp_folder, 'zip', temp_folder)
    shutil.rmtree(temp_folder)


def prepare_article(request, article, temp_folder, article_only=False):
    """
    Prepares an article for portico export
    :param request: HttpRequest
    :param article: Article object
    :param temp_folder: Folder string
    :param article_only Boolean
    :return: None
    """
    if article_only:
        article_folder = temp_folder
    else:
        article_folder = os.path.join(temp_folder, str(article.pk))

    files.mkdirs(article_folder)
    galleys = article.galley_set.all()

    xml_galleys = galleys.filter(type='xml')
    for xml_galley in xml_galleys:
        files.copy_file_to_folder(
            xml_galley.file.self_article_path(),
            xml_galley.file.uuid_filename,
            article_folder,
        )
        for image in xml_galley.images.all():
            files.copy_file_to_folder(
                image.self_article_path(),
                image.original_filename,
                article_folder,
            )
    if not xml_galleys.exists():
        generate_jats_metadata(request, article, article_folder)

    pdfs = core_models.Galley.objects.filter(
        article=article,
        file__mime_type='application/pdf',
    )
    for pdf in pdfs:
        files.copy_file_to_folder(
            file_path(article.pk, pdf.file.uuid_filename),
            pdf.file.uuid_filename, article_folder,
        )

    html_galleys = galleys.filter(type='html')
    for html_galley in html_galleys:
        files.copy_file_to_folder(
            file_path(article.pk, html_galley.file.uuid_filename),
            html_galley.file.uuid_filename,
            article_folder,
        )
        for image in html_galley.images.all():
            files.copy_file_to_folder(
                image.self_article_path(),
                image.original_filename,
                article_folder,
            )


def prepare_export_for_issue(request, file=False):
    """
    Prepares an export for an issue
    :param request: HttpRequest object
    :param file: Boolean, returns a file path rather than a HttpRequest
    :return: Streaming zip file
    """
    issue_id = request.POST.get('export-issue', None)
    issue = get_object_or_404(models.Issue, pk=issue_id, journal=request.journal)

    temp_folder, folder_string = prepare_temp_folder(request, issue=issue)

    print('Processing {issue}'.format(issue=issue))

    for article in issue.articles.all():
        prepare_article(request, article, temp_folder)

    zip_portico_folder(temp_folder)

    if file:
        return [
            '{folder}.zip'.format(folder=temp_folder),
            '{filename}.zip'.format(filename=folder_string)
        ]

    return files.serve_temp_file('{folder}.zip'.format(folder=temp_folder),
                                 '{filename}.zip'.format(filename=folder_string))


def prepare_export_for_article(request):
    """
    Prepares a single article for portico export
    :param request: HttpRequest
    :return: Streaming zip file
    """
    article_id = request.POST.get('export-article')
    article = get_object_or_404(submission_models.Article, pk=article_id, journal=request.journal)

    issue = article.primary_issue if article.primary_issue else article.issue
    temp_folder, folder_string = prepare_temp_folder(request, issue=issue, article=article)
    prepare_article(request, article, temp_folder, article_only=True)
    zip_portico_folder(temp_folder)

    return files.serve_temp_file('{folder}.zip'.format(folder=temp_folder),
                                 '{filename}.zip'.format(filename=folder_string))


def get_articles(request):
    """
    Returns a QuerySet of articles suitable for export
    :param request: HttpRequest
    :return: QuerySet of articles
    """
    return submission_models.Article.objects.filter(date_published__isnull=False,
                                                    stage=submission_models.STAGE_PUBLISHED,
                                                    journal=request.journal)
