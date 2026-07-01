## NODE

### Node — Yes/No

| # | Template |
|---|----------|
| N-YN-1 | Was `{player_name}` in the starting lineup for `{match_label}`? |
| N-YN-5 | Did `{match_label}` go into extra time? |
| N-YN-7 | Did `{match_label}` go to a shootout? |
| N-YN-8 | In `{match_label}`, does `{player_name}` wear jersey number `{n}`? |

### Node — long answer

| # | Template |
|---|----------|
| N-LA-1 | What jersey number does `{player_name}` wear in `{match_label}`? |
| N-LA-2 | What was the final score of `{match_label}`? |
| N-LA-3 | At what time did `{match_label}` kick off? |
| N-LA-4 | What is the number of goals scored by the away team in the `{match_label}`? |

---

## EDGE

### Edge — Yes/No

| # | Template |
|---|----------|
| E-YN-1 | In `{match_label}`, did `{player_name}` assist the goal scored by `{scorer_name}`? |
| E-YN-2 | Was `{player_name}` substituted out during `{match_label}`? |
| E-YN-4 | Did `{referee_name}` officiate `{match_label}`? |
| E-YN-6 | In `{match_label}`, is `{team_name}` the home team? |

### Edge — long answer

| # | Template |
|---|----------|
| E-LA-1 | Who assisted the goal scored by `{scorer_name}` in `{match_label}`? |
| E-LA-3 | Who refereed `{match_label}`? |
| E-LA-4 | In which competition was `{match_label}` played? |
| E-LA-5 | Which team was the away side in `{match_label}`? |

---

## SUBGRAPH

### Subgraph — Yes/No (single-match)

| # | Template |
|---|----------|
| S-YN-9 | Did `{player_name}` both score and assist in `{match_label}`? |

### Subgraph — Yes/No (cross-match)

| # | Template |
|---|----------|
| X-YN-2 | Did `{team_name}` win every match they played in the tournament? |
| X-YN-4 | Did any player from `{team_name}` score in `{n}` or more different matches? |
| X-YN-5 | Did `{referee_name}` show more cards than any other referee in the tournament? |

### Subgraph — long answer (cross-match)

| # | Template |
|---|----------|
| X-LA-1 | Who scored the most goals across all matches in the tournament? |
| X-LA-2 | Who were the top `{n}` goalscorers in the tournament, with their totals? | 
| X-LA-3 | How many goals were scored in total across the whole tournament? |
| X-LA-4 | Which team scored the most goals overall in the tournament? |
| X-LA-5 | Which player provided the most assists across all matches? |
| X-LA-6 | How many yellow and red cards were shown across the whole tournament? |
| X-LA-7 | Which referee officiated the most matches in the tournament? |
| X-LA-8 | What is the average number of goals per match in the tournament? | 
| X-LA-9 | Which match had the most goals, and how many? | 
| X-LA-10 | How many penalties were scored across the whole tournament? | 
| X-LA-12 | List each team's total goals scored across the tournament. | 
| X-LA-13 | How many matches in the tournament went to extra time or a shootout? |

