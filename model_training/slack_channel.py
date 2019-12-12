#!/usr/bin/env python3

"""
Requires the `inquirer` module to be installed
pip install inquirer
"""

import argparse
import inquirer
import json
import os
import random
import shutil
import slacker
import sys
import time
from inquirer.render.console import ConsoleRender
from inquirer.themes import GreenPassion
from requests import Session
from typing import Any, Dict, List, Optional, Set, Tuple

import training_util


DEFAULT_DATA_FILE = os.path.realpath(os.path.join(os.path.dirname(__file__), 'slack_channel_data/latest.json'))
DEFAULT_MODEL_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), 'slack_channel_model'))
DEFAULT_BATCH_SIZE = 10
USERS_CACHE = {}
IGNORE_LABEL = 'ignore'
CREATE_LABEL = '+add new'
INQUIRER_RENDER = ConsoleRender(theme=GreenPassion())


def get_client(token: str, session: Optional[Session] = None) -> slacker.Slacker:
    if not token:
        raise Exception(f'No token was provided')
    if not token.startswith('xoxp-'):
        raise Exception(f'The provided token is invalid since it not a user token, please use a user token instead')
    return slacker.Slacker(token, session=session)


def get_channel_id(token: str, name: str, session: Optional[Session] = None) -> str:
    # Strip off # prefix if specified
    if name.startswith('#'):
        name = name[1:]

    client = get_client(token, session=session)
    first_query = True
    cursor = None
    while first_query or cursor:
        first_query = False
        response = client.conversations.list(types=['public_channel', 'private_channel'], cursor=cursor)
        channels = response.body['channels']
        for channel in channels:
            if channel['name'] == name:
                return channel['id']
        cursor = response.body.get('response_metadata', {}).get('next_cursor')
    raise Exception(f'Could not find channel {name} in list of channels for this user')


def get_messages(token: str, channel_id: str, latest_timestamp: Optional[str],
                 batch_size: Optional[int], session: Optional[Session] = None) -> Tuple[List[dict], Optional[str]]:
    """
    Retrieves a list of messages, sorted in reverse age order, as well as the latest timestamp
    :return: Tuple of messages sorted in reverse age order and the latest timestamp
    """
    client = get_client(token, session=session)
    response = client.conversations.history(channel_id, limit=batch_size, latest=latest_timestamp)
    # The messages are already in reverse age order, with the latest first
    messages = response.body['messages']
    # Set the latest timestamp to the oldest message's timestamp
    latest_timestamp = messages[-1]['ts'] if len(messages) > 0 else None
    return messages, latest_timestamp


def get_data_labels(data: Dict[str, dict]) -> Set[str]:
    """
    Retrieves all labels that have already been classified.
    :param data:
    :return:
    """
    # Always remove the ignore label
    return set(data[elem]['label'] for elem in data).difference([IGNORE_LABEL])


def print_classification_entries(classifications: Dict[str, dict]):
    for message_id, classification in classifications.items():
        print(f'Text: {classification["text"]}')
        print(f'Label: {classification["label"]}')


def get_label(existing_labels: Set[str]) -> str:
    label = inquirer.list_input(
        'Please choose a label to apply to this message',
        choices=[IGNORE_LABEL] + sorted(existing_labels) + [CREATE_LABEL],
        render=INQUIRER_RENDER
    )
    if label == CREATE_LABEL:
        label = create_label(existing_labels)
        if not label:
            return get_label(existing_labels)
        # Add new label to the set of existing labels
        existing_labels.add(label)
    return label


def create_label(existing_labels: Set[str]) -> Optional[str]:
    new_label = inquirer.text(
        message="New label name (enter CANCEL to select an existing label)", render=INQUIRER_RENDER
    )
    if new_label == 'CANCEL':
        # Return nothing to cancel
        return None
    if not new_label or new_label in existing_labels or new_label == CREATE_LABEL:
        print(f'Error: new label "{new_label}" is invalid, '
              f'it may already exist or be reserved, please try again')
        return create_label(existing_labels)
    return new_label


def classify_batch(messages: List[dict], data: Dict[str, dict], all_labels: Set[str],
                   ignore_user_ids: Optional[Set[str]] = None) -> Tuple[Dict[str, dict], Dict[str, dict]]:
    messages_len = len(messages)
    added = {}
    updated = {}
    for i, message in enumerate(messages):
        message_text = message.get('text') or '<NO TEXT>'
        message_id = f'{message.get("ts")}-{message.get("user")}'
        print(f'{i + 1}/{messages_len} {message_text}')
        if not message.get('text') or message.get('attachments') or message.get('blocks'):
            print('Message has no text or attachments/blocks, skipping')
            continue
        message_user = message.get('user')
        if ignore_user_ids and message_user in ignore_user_ids:
            print(f'Message is from an ignored user ID ({message_user}), skipping')
            continue

        classification = data.get(message_id)
        if classification:
            # Update classification text if it was modified
            changed = False
            if message_text != classification.get('text'):
                classification['text'] = message_text
                changed = True

            # A classification already exists for this message
            if not inquirer.confirm(f'There is already an existing classification for this message'
                                    f'{"(text has been modified)" if changed else ""}, '
                                    f'do you want to change it from {classification["label"]}?',
                                    render=INQUIRER_RENDER):
                continue

            # Copy the classification so that it can modified multiple times if there are problems
            updated[message_id] = classification.copy()
        else:
            # No classification exists, prompt to skip (classify as ignore) or add an operation for it
            classification = {
                'text': message_text,
                'label': None,
            }
            # Add to added dict
            added[message_id] = classification

        # Set classification label
        label = get_label(all_labels)
        classification['label'] = label

    print('--------------------------------------Summary----------------------------------------')
    if updated:
        print(f'Updated {len(updated)} existing classification(s):')
        print_classification_entries(updated)
    if added:
        print(f'Added {len(added)} new classification(s):')
        print_classification_entries(added)
    else:
        print('No new classification entries added')
    if not inquirer.confirm('Are the above entries correct?', default=True, render=INQUIRER_RENDER):
        return classify_batch(messages, data, all_labels, ignore_user_ids=ignore_user_ids)

    return added, updated


def classify_messages(token: str, channel_id: str, data: Dict[str, dict], latest_timestamp: Optional[str],
                      ignore_user_ids: Optional[Set[str]], batch_size: Optional[int] = None,
                      session: Optional[Session] = None) -> Optional[str]:
    all_labels = get_data_labels(data)
    done = False
    while not done:
        messages, latest_timestamp = get_messages(token, channel_id, latest_timestamp, batch_size, session=session)
        print('-------------------------------------------------------------------------------------')
        print(f'Retrieved new batch of {len(messages)} message{"s" if len(messages) > 1 else ""} '
              f'(latest timestamp is {latest_timestamp})')
        added, updated = classify_batch(messages, data, all_labels, ignore_user_ids=ignore_user_ids)
        for message_id, classification in added.items():
            data[message_id] = classification
        for message_id, classification in updated.items():
            data[message_id] = classification

        if not inquirer.confirm(f'{len(data)} total messages classified, continue to the next batch of messages?',
                                default=True, render=INQUIRER_RENDER):
            done = True

    return latest_timestamp


def load_data(data_file: str, append: bool = True) -> Tuple[dict, Optional[str]]:
    if not os.path.exists(data_file):
        return {}, None

    if not append:
        raise Exception(
            f'The data file ({data_file}) exists and append is disabled, please specify another data file'
        )

    # Load existing data
    with open(data_file, 'r') as fobj:
        data = json.loads(fobj.read())
        if not data:
            raise Exception(f'The existing data file ({data_file}) is invalid, please check the file')
        return data.get('data', {}), data.get('latest_timestamp')


def write_data(data: Dict[str, dict], latest_timestamp: Optional[str], data_file: str):
    # Make the directory first
    dir_path = os.path.dirname(data_file)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    # Write out the new file
    with open(data_file, 'w') as fobj:
        fobj.write(json.dumps({
            'data': data,
            'latest_timestamp': latest_timestamp,
        }, indent=2))
        print(f'Successfully wrote data to {data_file}')

    # Copy the result file to a file versioned with a timestamp
    shutil.copy(data_file, f'{data_file}.{time.time()}')


def test_model(args):
    if not args.model_dir:
        raise Exception('The model dir was not specified, please try again')
    if not args.test_text and not args.test_file:
        raise Exception('Text to test must be provided')

    print(f'Loading model from {args.model_dir}')

    has_failures = False
    if args.test_file:
        with open(args.test_file, 'r') as fobj:
            file_contents = fobj.read()
        for i, line in enumerate(file_contents.splitlines()):
            elems = line.split('\t')
            if len(elems) != 2:
                raise Exception(
                    f'Line {i + 1} of {args.test_file} is invalid, '
                    f'it should contain two tab-separated values, but has {len(elems)}'
                )
            if not training_util.test_textcat_model(args.model_dir, elems[0], elems[1]):
                has_failures = True
    else:
        if not training_util.test_textcat_model(args.model_dir, args.test_text, args.expected_label):
            has_failures = True

    if has_failures:
        print('Encountered verification errors, please see above')
        sys.exit(1)

    
def train(args):
    if not args.output_dir:
        raise Exception('The output dir was not specified, please try again')

    data, _ = load_data(args.data_file)
    labels = set(data[key]['label'] for key in data)

    def get_labels(true_label: str) -> Dict[str, bool]:
        nonlocal labels
        result = {}
        for label in labels:
            result[label] = true_label == label
        return result

    def data_func() -> Tuple[
        List[Tuple[Any, Dict[str, Dict[str, bool]]]], List[Tuple[Any, Dict[str, Dict[str, bool]]]]
    ]:
        nonlocal data
        limit = len(data)
        train_limit = int(limit * 0.8)
        tuple_data = []
        for _, classification in data.items():
            tuple_data.append(
                (classification['text'], {'cats': get_labels(classification['label'])})
            )
        # Randomize the list
        random.shuffle(tuple_data)
        return tuple_data[:train_limit], tuple_data[train_limit:]

    training_util.train_textcat_model(
        load_data_func=data_func, output_dir=args.output_dir, labels=labels, test_text=args.test_text
    )
    

def classify(args):
    # Parse ignore user ids from comma-separated list
    if args.ignore_user_ids:
        ignore_user_ids = set(args.ignore_user_ids.split(','))
    else:
        ignore_user_ids = None
        
    # with Session() as session:
    channel_id = get_channel_id(args.slack_token, args.slack_channel)
    data, latest_timestamp = load_data(args.data_file, args.append)
    latest_timestamp = classify_messages(
        args.slack_token,
        channel_id,
        data,
        # Override the latest timestamp to use if specified
        args.latest_timestamp or latest_timestamp,
        ignore_user_ids=ignore_user_ids,
        batch_size=args.batch_size,
        )
    write_data(data, latest_timestamp, args.data_file)


def main():
    parser = argparse.ArgumentParser(description='Makes it easy to train a model based on messages in a slack channel')
    parser.add_argument(
        "-d", "--data-file",
        dest="data_file",
        default=DEFAULT_DATA_FILE,
        help=f"The data file to use for storage, defaults to '{DEFAULT_DATA_FILE}'",
    )

    subparsers = parser.add_subparsers(title='command')

    train_parser = subparsers.add_parser('train', description='Train a model from the classified data file')
    train_parser.add_argument(
        "-o", "--output-dir",
        dest="output_dir",
        default=DEFAULT_MODEL_DIR,
        help=f"The output directory for the model, defaults to {DEFAULT_MODEL_DIR}",
    )
    train_parser.add_argument(
        "-t", "--test-text",
        dest="test_text",
        help="Text to use for a test at the end of training",
    )
    train_parser.set_defaults(func=train)

    test_parser = subparsers.add_parser('test', description='Test a trained model\'s output')
    test_parser.add_argument(
        "-m", "--model-dir",
        dest="model_dir",
        default=DEFAULT_MODEL_DIR,
        help=f"The directory for the model, defaults to {DEFAULT_MODEL_DIR}",
    )
    test_parser.add_argument(
        "-e", "--expected-label",
        dest="expected_label",
        help="The label expected to be generated with the best score from the test",
    )
    test_parser.add_argument(
        "-t", "--test-text",
        dest="test_text",
        help="Text to use for a test, if it is a file, "
             "read the file as tab separated with the text first and expected label second",
    )
    test_parser.add_argument(
        "-f", "--test-file",
        dest="test_file",
        help="Test file that is tab separated with the text first and expected label second",
    )
    test_parser.set_defaults(func=test_model)

    classify_parser = subparsers.add_parser('classify', description='Classify messages from slack')
    classify_parser.add_argument(
        "slack_channel",
        help="The slack channel to pull messages from, with or without the # prefix",
    )
    classify_parser.add_argument(
        "-b", "--batch-size",
        dest="batch_size",
        default=DEFAULT_BATCH_SIZE,
        type=int,
        help=f"The number of messages to retrieve at a time, defaults to {DEFAULT_BATCH_SIZE}",
    )
    classify_parser.add_argument(
        "-i", "--ignore-user_ids",
        dest="ignore_user_ids",
        default=os.environ.get('SLACK_IGNORE_USER_IDS'),
        help="May be set to a comma separated list of user IDs (e.g. W3J13MBJA) that should be ignored. "
             "Pulled from the SLACK_IGNORE_USER_IDS environment variable if not set.",
    )
    classify_parser.add_argument(
        "-o", "--no-overwrite",
        action="store_false",
        dest="append",
        help="If set, does not append data to the data file and errors out if the file already exists",
    )
    classify_parser.add_argument(
        "-l", "--latest-timestamp",
        dest="latest_timestamp",
        help="Sets the latest timestamp to use instead of ",
    )
    classify_parser.add_argument(
        "-t", "--token",
        dest='slack_token',
        default=os.environ.get('SLACK_TOKEN'),
        help="The slack token to use for authentication, pulled from the SLACK_TOKEN environment variable if not set. "
             "This MUST be a user token and not a bot token due to the permissions needed for conversation history.",
    )
    classify_parser.set_defaults(func=classify)

    args = parser.parse_args()
    if not hasattr(args, 'func'):
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)
    


if __name__ == '__main__':
    main()
