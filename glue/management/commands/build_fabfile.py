from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create a fabfile.py from template'

    def handle(self, *app_labels, **options):
        from django.template.loader import get_template
        from django.template import Context
        import sys

        t = get_template('glue/fabfile_template.py')
        out = t.render(Context({}))

        sys.stdout.write(out)
