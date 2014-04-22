import bs4 as bs
import requests as r
import re
import pandas as pd

ESPN_BASE_URL = 'http://scores.espn.go.com'
NBA_BASE_URL = 'http://scores.espn.go.com/nba/scoreboard'

SCORE_RE = r'[0-9]*\-[0-9]*$'
TIMESTAMP_RE = r'[0-9]*:[0-9]*$'
GAME_NUMBER_RE = r'Game ([0-7]) of 7'
# Could be either a half (in NCAA) or quarter (in NBA)
END_OF_PERIOD_RE = r'End of'

def parse_time(time_str):
    ''' 
    input: a string like <MINUTE>:<SECONDS>
    '''
    minutes, seconds = time_str.split(':')
    
    return float(minutes) + float(seconds) / 60

def convert_global_time(relative_time, quarter):
    '''
    Returns the minute (in range 0 - 48) of the time represented
    by <relative_time> in the <quarter>th quarter
    '''
    since_start_of_quarter = 12.0 - relative_time
    global_time = 12.0 * (quarter - 1) + since_start_of_quarter

    return global_time

def make_uniform_time_intervals(events, times):
    '''
    Based on the game stored in <events>, make a new list of events (dictionaries)
    with scores for each time in <times>

    Useful for comparing games
    '''
    new_events = []

    event_index = 0
    cur_event = events[event_index]

    for t in times:
        while t > cur_event['time']:
            # Move to the next event, if possible
            if event_index < len(events) - 1:
                event_index += 1
                cur_event = events[event_index]
            # Otherwise we've gone through every event
            else:
                break

        # Copy cur_event, but set its time to be <t>
        event = {k : v for k, v in cur_event.items()}
        event['time'] = t
        new_events.append(event)

    return new_events

def parse_team_names(soup):
    '''
    Grab the team names from summary/linescore table
    '''
    linescore_table = soup.find('table', {'class' : 'linescore'})
    away_name, home_name = [t.text for t in linescore_table.find_all('a')]

    return away_name, home_name

def parse_game_num(soup):
    '''
    Parse the game number (out of 7) from this soup
    '''
    matches = [re.search(GAME_NUMBER_RE, p.text) for p in soup.find_all('p')]
    game_nums = [m.group(1) for m in matches if m is not None]

    # Should only be one match, parse the game numebr from the first group
    if len(game_nums) == 1:
        return int(game_nums[0])
    else:
        print('No game number found!')
        return -1


def parse_game_urls(scoreboard_url=None):
    '''
    Scrape <scoreboard_url> and extract any URLs that lead to Play-by-Plays.
    Returns relative URLs (such as '/nba/playbyplay?gameId=400489876')
    to be joined with the base ESPN url 
    '''
    if scoreboard_url is None:
        scoreboard_url = 'http://scores.espn.go.com/nba/scoreboard?date=20140318'

    response = r.get(scoreboard_url)
    html = response.text
    soup = bs.BeautifulSoup(html)

    all_links = soup.find_all('a')
    game_urls = []

    for link in all_links:
        if 'Play‑By‑Play' in link.text:
            game_urls.append(link['href'])

    return [ESPN_BASE_URL + u for u in game_urls]

def process_one_game(url, round_num, time_intervals=None):
    '''
    Returns list of dictionaries storing events for game with play-by-play
    URL given by <url>
    '''
    print('Working on', url)
    response = r.get(url)
    html = response.text
    soup = bs.BeautifulSoup(html)

    away_name, home_name = parse_team_names(soup)
    game_num = parse_game_num(soup)

    # TODO grab ranks from somewhere
    #rank_diff = abs(away_rank - home_rank)
    game_id = '%s-%s-%i' % (away_name, home_name, game_num)

    # Store which team has "better" rank, i.e. a lower number
    #home_higher_rank = home_rank < away_rank

    period = 1
    previous_away_score = 0
    previous_home_score = 0

    # A list of dictionaries
    all_events = []
    rows = soup.find_all('tr')

    for row in rows:
        # Only create an event on rows with scoring events
        event_row = False

        cols = row.find_all('td')
        for col in cols:
            if re.match(SCORE_RE, col.text):
                away_score, home_score = [int(s) for s in col.text.split('-')]

                # Only save an event if one of the scores changed
                event_row = away_score != previous_away_score or home_score != previous_home_score
                previous_away_score = away_score
                previous_home_score = home_score

            if re.match(TIMESTAMP_RE, col.text):
                cur_time = parse_time(col.text)
                
            if re.match(END_OF_PERIOD_RE, col.text):
                period += 1

            if event_row:
                # TODO make this in terms of ranking
                diff_score = away_score - home_score
                global_time = convert_global_time(cur_time, period)

                event = {
                    'game_id' : game_id,
                    'round_num' : round_num,
                    'away' : away_name,
                    # 'away_rank' : away_rank,
                    'home' : home_name,
                    # 'home_rank' : home_rank,
                    'time' : global_time,
                    'away_score' : away_score,
                    'home_score' : home_score,
                    'diff_score' : diff_score,
                    # 'rank_diff' : rank_diff
                }
                all_events.append(event)

    if time_intervals is None:
        return all_events
    else:
        return make_uniform_time_intervals(all_events, time_intervals)

def process_one_day(scoreboard_url, round_num, time_intervals=None):
    '''
    Returns list of dictionaries containing events from all games linked to
    by <scoreboard_url> i.e. all the games played on given day
    '''
    game_urls = parse_game_urls(scoreboard_url)

    # A list of dictionaries
    all_games = []
    for url in game_urls:
        all_games += process_one_game(url, round_num, time_intervals)

    return all_games

def process_playoffs(outfile='nba_data/example_pbp.csv', time_intervals=None):
    april = 20140400
    day_to_round = {
        19 : 1,
        20 : 1,
        21 : 1,
        22 : 1
    }
    # Looking at April 19 - 22 for the moment
    days = day_to_round.keys()
    dates = [april + d for d in days]

    # List of dictionaries
    all_games = []
    for day in days:
        day_url = NBA_BASE_URL + '?date=' + str(april + day)
        all_games += process_one_day(day_url, day_to_round[day], time_intervals)

    df = pd.DataFrame(all_games)
    df.to_csv(outfile, index=False)

if __name__ == '__main__':
    # From 0 --> 40.75
    times = [.25 * t for t in range(4 * 49)]
    # If no <time_intervals> argument is passed, events will be recorded at actual
    # time in the play by play
    process_playoffs(time_intervals=times)

    # url = 'http://scores.espn.go.com/nba/playbyplay?gameId=400553081&period=0'
    # events = process_one_game(url, -1, times)
    # for e in events:
    #     print(e)

    
