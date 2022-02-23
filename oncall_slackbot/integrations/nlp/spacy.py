# -*- coding: utf-8 -*-

import logging
from typing import Optional
import spacy  # pylint: disable=import-error
from spacy.language import Doc, Language  # pylint: disable=import-error
from oncall_slackbot import settings


LOGGER = logging.getLogger(__name__)

_NLP = None


def is_configured() -> bool:
    return not not settings.SPACY_MODEL  # pylint: disable=unneeded-not


def _initialize_textcat(nlp: Language) -> None:
    # Ensure that the text categorizer is added to the pipeline
    if 'textcat' not in nlp.pipe_names:
        LOGGER.info('Adding the text categorizer to the spacy nlp pipeline')

        # nlp.create_pipe works for built-ins that are registered with spaCy
        textcat = nlp.create_pipe(
            'textcat', config={'exclusive_classes': True, 'architecture': 'simple_cnn'}
        )
        nlp.add_pipe(textcat, last=True)


def _get_nlp() -> Optional[Language]:
    global _NLP  # pylint: disable=global-statement
    if not is_configured():
        return None
    if not _NLP:
        LOGGER.debug('Loading spacy model from %s', settings.SPACY_MODEL)
        _NLP = spacy.load(settings.SPACY_MODEL)
        _initialize_textcat(_NLP)
        LOGGER.info('Initialized spacy nlp backend from model %s', settings.SPACY_MODEL)
    return _NLP


def get_doc(message_text: str) -> Optional[Doc]:
    if not message_text:
        return None
    nlp = _get_nlp()
    if not nlp:
        return None
    return nlp(message_text)


def generate_label(message_text: str) -> Optional[str]:
    doc = get_doc(message_text)
    if not doc:
        return None
    return max(doc.cats.keys(), key=lambda cat: doc.cats[cat])


# Always pre-initialize the backend if possible
_get_nlp()
