"""Small synthetic quality comparison. Opt in with --run; never reads user data.

Run with the application's existing key in its environment, never in arguments.
This is a qualitative sample, not a claim that a model is flawless.
"""
import argparse
import json
import os
import time
from types import SimpleNamespace
from nova import ai


def evaluate(models):
    voice = SimpleNamespace(writing_tone='Warm, dry British humour. Short sentences. No emojis or hashtags.',
        audience='UK women 25–35', topics='Affordable everyday style',
        things_to_avoid='game-changer, obsessed, elevate, must-have, unlock. Never invent benefits or personal experience.',
        preferred_post_length=220, example_posts='Wore this three times this week. Calling it outfit research.\nThe bag has pockets. My standards are apparently very specific.')
    cases = [
        ('one_off', lambda: ai.generate_variants(brief='Draft an Instagram caption for my Brixton gym. A one-off beginners strength class this Saturday at 10am. DM START to book a trial. Under 45 words. Do not invent the price or duration. Do not include TEST DRAFT.', instruction='', platforms=['instagram'], thread_length=1, preferences=SimpleNamespace(writing_tone='Friendly and practical'))),
        ('affiliate', lambda: ai.generate_variants(brief='Instagram caption for a £35 jacket, full price. Start Ad | Affiliate link. I earn commission from the link in bio. Under 45 words. I have not tested it in rain; do not claim waterproof. Encourage clicks, not saves.', instruction='Private production plan: one-take video. Private measurement: track clicks for seven days. Do not print these plans.', platforms=['instagram'], thread_length=1, preferences=voice)),
        ('rewrite_both', lambda: ai.rewrite_variant(platform='instagram', posts=['Three looks, one £35 jacket. Which would you wear — 1, 2 or 3? Tell me why! Not sponsored.'], action='instruction', instruction='Make both captions sound like my writing examples: dry humour, no exclamation marks. Remove Not sponsored because this is not an ad. Keep £35 and the 1/2/3 choice.', preferences=voice)),
        ('supplied_results', lambda: ai.analyse_performance(question='These are hypothetical figures I supply, not connected data: Reel A: 10,000 views, 80 saves, 40 comments, 100 clicks, 2 sales. Reel B: 4,000 views, 120 saves, 20 comments, 80 clicks, 8 sales. Which should I repeat for sales? Suggest one fair experiment.', dashboard={}, preferences=voice)),
    ]
    original = os.environ.get('OPENAI_MODEL')
    original_content = os.environ.get('OPENAI_CONTENT_MODEL')
    try:
        for model in models:
            os.environ['OPENAI_MODEL'] = model
            os.environ['OPENAI_CONTENT_MODEL'] = model
            for name, operation in cases:
                started = time.monotonic()
                try: result = {'output': operation()}
                except Exception as exc: result = {'error_type': type(exc).__name__}  # No credentials/provider body.
                print(json.dumps({'model': model, 'case': name, 'seconds': round(time.monotonic()-started, 2), **result}, ensure_ascii=False), flush=True)
    finally:
        if original is None: os.environ.pop('OPENAI_MODEL', None)
        else: os.environ['OPENAI_MODEL'] = original
        if original_content is None: os.environ.pop('OPENAI_CONTENT_MODEL', None)
        else: os.environ['OPENAI_CONTENT_MODEL'] = original_content


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--models', nargs='+', default=['gpt-5-mini', 'gpt-6.1-terra'])
    args = parser.parse_args()
    if args.run: evaluate(args.models[:2])
    else: print('Dry run: four synthetic cases per model. Use --run to make API requests.')
