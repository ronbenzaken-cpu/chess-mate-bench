# Results

30 calls: 3 puzzles x 1 models x 2 thinking modes x 5 runs.
Models: haiku = `claude-haiku-5-5`, sonnet = `claude-sonnet-5-5`, opus = `claude-opus-5-5`

## Expected vs actual (solved = at least 3/5 passes)

| Model | Thinking | Expected to solve | Actually solved | Hypothesis |
|---|---|---|---|---|
| haiku | thinking=0 | none | 1, 2, 3 | rejected |
| haiku | thinking=default | 1 | 1, 2, 3 | rejected |

## Pass rate (first move forces mate)

| Puzzle | Mate in | haiku thinking=0 | haiku thinking=default |
|---|---|---|---|
| 1. Scholar's Mate | 1 | 5/5 | 5/5 |
| 2. Philidor's Legacy (smothered mate) | 2 | 3/5 | 3/5 |
| 3. Morphy's Opera Game finish | 2 | 5/5 | 5/5 |

## Full line correct

| Puzzle | Mate in | haiku thinking=0 | haiku thinking=default |
|---|---|---|---|
| 1. Scholar's Mate | 1 | 5/5 | 5/5 |
| 2. Philidor's Legacy (smothered mate) | 2 | 3/5 | 3/5 |
| 3. Morphy's Opera Game finish | 2 | 5/5 | 5/5 |

## Failure categories

| Category | Count |
|---|---|
| gave_up | 4 |

## Failures

- 2. Philidor's Legacy (smothered mate) | haiku | thinking=0 | run 3 | gave_up: no move given: 'No forced mate in 2 found'
- 2. Philidor's Legacy (smothered mate) | haiku | thinking=0 | run 5 | gave_up: no move given: 'no forced mate in 2 found'
- 2. Philidor's Legacy (smothered mate) | haiku | thinking=default | run 3 | gave_up: no move given: 'No forced mate in 2 found'
- 2. Philidor's Legacy (smothered mate) | haiku | thinking=default | run 4 | gave_up: no move given: 'no forced mate in 2 found'
