# whoops, i guess there's already a CLI for deepl python
# https://github.com/DeepLcom/deepl-python#command-line-interface
# but this has fewer flags and options than theirs.
# https://github.com/DeepLcom/deepl-python#glossaries
import deepl
import os
import click
import json

TRANSLATOR = deepl.Translator(os.environ['DEEPL_AUTH_KEY'])

@click.group()
def cli():
    pass

@cli.command()
@click.argument('input', type=click.File('rb'))
def translate():


@cli.command()
def list():
    g = TRANSLATOR.list_glossaries()
    if g:
        print("Glossary List")
        print("-------------")
        for glossary in g:
            print(glossary)
    else:
        print("No glossaries found")

@cli.command()
@click.argument('input', type=click.File('rb'))
@click.option('--name', '-n', default="weatherbot", help='The glossary name, used when initializing a translator later.')
def load(input, name):
    glossary = json.load(input)
    TRANSLATOR.create_glossary(
        name,
        source_lang='EN',
        target_lang='ES',
        entries=glossary
    )
    click.echo(f"Created glossary {name}")

if __name__ == '__main__':
    cli()
