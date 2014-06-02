import bs4 as bs
import requests as r
import re
import pandas as pd
import datetime

ESPN_BASE_URL = 'http://scores.espn.go.com'
NBA_BASE_URL = 'http://scores.espn.go.com/nba/scoreboard'

SCORE_RE = r'[0-9]*\-[0-9]*$'
TIMESTAMP_RE = r'[0-9]*:[0-9]*$'
GAME_NUMBER_RE = r'Game ([0-7]) of '
# Could be either a half (in NCAA) or quarter (in NBA)
END_OF_PERIOD_RE = r'End of'

TEAM_TO_SEED = {
    'IND' : 1, 'SA' : 1,
    'MIA' : 2, 'OKC' : 2,
    'TOR' : 3, 'LAC' : 3,
    'CHI' : 4, 'HOU' : 4,
    'WSH' : 5, 'POR' : 5,
    'BKN' : 6, 'GS' : 6,
    'CHA' : 7, 'MEM' : 7,
    'ATL' : 8, 'DAL' : 8
}

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
    team_links = linescore_table.find_all('a')

    # Have to create a special case for Bobcats -- since they're once
    # again the Hornets, the link to Bobcats is broken! Should only happen
    # in the Heat-Bobcats (or should I say "Hornets") series
    if len(team_links) == 2:
        away_name, home_name = [t.text for t in team_links]
    elif len(team_links) == 1:
        away_name = 'CHA'
        home_name = team_links[0].text

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


def parse_game_urls(scoreboard_url=None, url_params=None):
    '''
    Scrape <scoreboard_url> and extract any URLs that lead to Play-by-Plays.
    Returns relative URLs (such as '/nba/playbyplay?gameId=400489876')
    to be joined with the base ESPN url 
    '''
    soup = make_soup(scoreboard_url, url_params)

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
    soup = make_soup(url)

    away_name, home_name = parse_team_names(soup)
    game_num = parse_game_num(soup)

    # TODO grab ranks from somewhere
    away_rank = TEAM_TO_SEED[away_name]
    home_rank = TEAM_TO_SEED[home_name]

    rank_diff = abs(away_rank - home_rank)
    game_id = '%s-%s-%i' % (away_name, home_name, game_num)

    # Store which team has "better" rank, i.e. a lower number
    home_higher_rank = home_rank < away_rank

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
                diff_score = home_score - away_score if home_higher_rank else away_score - home_score
                global_time = convert_global_time(cur_time, period)

                event = {
                    'game_id' : game_id,
                    'round_num' : round_num,
                    'away' : away_name,
                    'away_rank' : away_rank,
                    'home' : home_name,
                    'home_rank' : home_rank,
                    'time' : global_time,
                    'away_score' : away_score,
                    'home_score' : home_score,
                    'diff_score' : diff_score,
                    'rank_diff' : rank_diff
                }
                all_events.append(event)

    if time_intervals is None:
        return all_events
    else:
        return make_uniform_time_intervals(all_events, time_intervals)

def process_one_day(scoreboard_url, url_params, round_num, time_intervals=None):
    '''
    Returns list of dictionaries containing events from all games linked to
    by <scoreboard_url> i.e. all the games played on given day
    '''
    print('Scoreboard URL:', scoreboard_url)
    game_urls = parse_game_urls(scoreboard_url, url_params)

    # A list of dictionaries
    all_games = []
    for url in game_urls:
        all_games += process_one_game(url, round_num, time_intervals)

    return all_games

def process_playoffs(outfile='nba_data/example_pbp.csv', time_intervals=None):
    start_date = datetime.date(2014, 4, 19)
    end_date = datetime.date(2014, 6, 1)
    
    all_dates, all_rounds = get_dates_in_range(start_date, end_date)

    # List of dictionaries
    all_games = []
    for date, round_num in zip(all_dates, all_rounds):
        date_param = {'date' : date.strftime('%Y%m%d')}
        all_games += process_one_day(NBA_BASE_URL, date_param, round_num, time_intervals)

    df = pd.DataFrame(all_games)
    df.to_csv(outfile, index=False)

def make_soup(url, params=None):
    response = r.get(url, params=params)
    soup = bs.BeautifulSoup(response.text)

    return soup

def get_dates_in_range(start_date, end_date):
    round_one = datetime.date(2014, 4, 19)
    round_two = datetime.date(2014, 5, 5)
    round_three = datetime.date(2014, 5, 18)

    one_day_delta = datetime.timedelta(days=1)

    all_dates = []
    all_rounds = []
    cur_date = start_date

    # I'm sure there's a list comprehension to do this, but oh well
    while cur_date <= end_date:
        all_dates.append(cur_date)

        # What round?
        if cur_date < round_three:
            if cur_date < round_two:
                all_rounds.append(1)
            else:
                all_rounds.append(2)
        else:
            all_rounds.append(3)

        cur_date += one_day_delta

    return all_dates, all_rounds

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

    
