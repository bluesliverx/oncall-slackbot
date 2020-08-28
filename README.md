A base for an on-call chat bot for [Slack](https://slack.com) and extends classes from
[lins05/slackbot](https://github.com/lins05/slackbot). While slackbot supports Python 2 and 3,
this repository is Python 3+ only.

This project was built during Adobe "Garage Week" 2019 in order to support the easy creation of
bots for on-call Slack channels that listen to events and can respond intelligently.

## Features

* [PagerDuty](https://www.pagerduty.com/) integration for querying on call information
* Natural language processing (NLP) support for smarter bots using [spaCy](https://spacy.io)
  * Currently only supports text categorization for message routing, but could support more in the future
* Supports Slack blocks in addition to attachments

## Usage

### Generate the slack api token

First you need to get the slack api token for your bot. You have two options:

1. If you use a [bot user integration](https://api.slack.com/bot-users) of slack, you can get the api token on the integration page.
2. If you use a real slack user, you can generate an api token on [slack web api page](https://api.slack.com/web).

### Perform lins05 setup

Follow the setup steps in the [lins05/slackbot](https://github.com/lins05/slackbot) repository.

### Configure PagerDuty integration

slackbot_settings.py:

```
PAGERDUTY_TOKEN = 'mytoken'
PAGERDUTY_SCHEDULE_ID = 'ABCDEFG'
PAGERDUTY_USERNAME_EMAIL_DOMAIN = 'adobe.com'
```

See the `slackbot/plugins/oncall.py` file for examples of using the PagerDuty integration.

### Configure spaCy integration

Before spaCy can be used, it must have a model trained for text categorization or text labels.
Please note that message routing is currently only capable based on labels and not any other
spaCy document properties.

#### Training a spaCy model

If you already have a spaCy textcat model to use, you may skip this section completely.

You can use [Yuri](https://github.com/bluesliverx/yuri) to classify slack messages,
train a spaCy model, and test it. In the end you should have a directory containing
the spaCy model files.

#### Configure spaCy model location

slackbot_settings.py:

```
SPACY_MODEL = '/model/dir'
```

This is the same directory that was generated using yuri or by manually training a spaCy model.

#### Use nlp responders in your plugins

See the `slackbot/plugins/nlp.py` file for examples of using NLP in your plugins.


# Releasing new versions

To release a new version of this library, install `bump2version` into a virtualenv, and then
call `bump2version <part>` where part is `major`, `minor`, or `patch` to update a certain part
of the version number. Then push the tag and the master branch. The tagged version will be
built on travis-ci.org and released to pypi and docker.

