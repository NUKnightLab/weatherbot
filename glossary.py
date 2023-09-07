# https://github.com/DeepLcom/deepl-python#glossaries
import deepl
import os
import click

TRANSLATOR = deepl.Translator(os.environ['DEEPL_API_KEY'])

@click.group()
def cli():
    pass

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

if __name__ == '__main__':
    cli()
