import random
import ssl #did not allow me to run code without this had to use chatgpt to know what this was
import os
import pandas as pd
import numpy as np
from openpyxl import load_workbook

current_year = 2024 #Set Starting Year and Week
current_week = 0
next_matchup = None #sets first weeks matchup to none and allows generate schedule function to take over
committed_recruits = [] #global list to append committed recruits who dont commit before week 1
committed_recruit_messages = [] #reprint message because of clear screen function
game_log = []
last_action_message = ""  #^
last_statistics_output = "" #^
offseason_messages = [] #^
tournament_messages = [] #^
scheduled_opponents = set()
user_team_info = {
    "school": None,
    "conference": None,
    "coach_name": None,
    "record": None
}

#sets real conference names for abbreviated columns from dataset
CONFERENCE_MAPPING = {
    'A10': 'Atlantic 10', 'ACC': 'Atlantic Coast Conference', 'AE': 'America East',
    'Amer': 'American Athletic Conference', 'ASun': 'Atlantic Sun', 'B10': 'Big Ten',
    'B12': 'Big 12', 'BE': 'Big East', 'BSky': 'Big Sky', 'BSth': 'Big South',
    'BW': 'Big West', 'CAA': 'Colonial Athletic Association', 'CUSA': 'Conference USA',
    'Horz': 'Horizon League', 'Ivy': 'Ivy League', 'MAAC': 'Metro Atlantic Athletic Conference',
    'MAC': 'Mid-American Conference', 'MEAC': 'Mid-Eastern Athletic Conference',
    'MVC': 'Missouri Valley Conference', 'MWC': 'Mountain West Conference', 'NEC': 'Northeast Conference',
    'OVC': 'Ohio Valley Conference', 'P12': 'Pac-12 Conference', 'Pat': 'Patriot League',
    'SB': 'Sun Belt', 'SC': 'Southern Conference', 'SEC': 'Southeastern Conference',
    'Slnd': 'Southland Conference', 'Sum': 'Summit League', 'SWAC': 'Southwestern Athletic Conference',
    'WAC': 'Western Athletic Conference', 'WCC': 'West Coast Conference'
}

# API link for Google Sheets
spreadsheet_id = "15nhT8U7DhZmnKUJ0eC4_G_D5KuGYx18RRygy13dvtgs"
gid = '1137186063' # Sheet ID
api_link = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?gid={gid}&tqx=out:csv"

def save_season_to_csv(game_log, year):
    if not game_log:
        print(f"No games to save for {year}.")
        return

    df = pd.DataFrame(flatten_game_log(game_log))
    file_path = "all_simulated_seasons_for_game.csv"

    try:
        existing_df = pd.read_csv(file_path)
        full_df = pd.concat([existing_df, df], ignore_index=True)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        full_df = df

    full_df.to_csv(file_path, index=False)
    print(f"Season {year} games appended to {file_path}.")


def flatten_game_log(game_log):
    flat_log = []
    for game in game_log:
        flat_game = {
            "year": game["year"],
            "week": game["week"],
            "opponent": game["opponent"],
            "result": game["result"],
            "team_score": game["team_score"],
            "opponent_score": game["opponent_score"],
            "period": game["period"]
        }
        stats = game["team_stats"]
        opp_stats = game["opponent_stats"]
        possessions = stats["possessions"]
        opp_possessions = opp_stats["possessions"]

        adj_off_eff = (stats["points"] / possessions) * 100 if possessions else 0
        adj_def_eff = (opp_stats["points"] / possessions) * 100 if possessions else 0
        power_rating = (adj_off_eff - adj_def_eff) + 100
        efg = (stats["FGM"] + 0.5 * 0) / stats["FGA"] if stats["FGA"] else 0  # No 3P info
        efg_d = (opp_stats["FGM"] + 0.5 * 0) / opp_stats["FGA"] if opp_stats["FGA"] else 0
        tor = stats["TO"] / possessions if possessions else 0
        tord = opp_stats["TO"] / opp_possessions if opp_possessions else 0
        orb = stats["REB"] / (stats["REB"] + opp_stats["REB"]) if (stats["REB"] + opp_stats["REB"]) else 0
        drb_allowed = opp_stats["REB"] / (opp_stats["REB"] + stats["REB"]) if (opp_stats["REB"] + stats["REB"]) else 0
        ftr = stats["FTM"] / stats["FGA"] if stats["FGA"] else 0
        ftrd = opp_stats["FTM"] / opp_stats["FGA"] if opp_stats["FGA"] else 0
        tempo = possessions

        flat_game.update({
            "Adjusted Offensive Efficiency": round(min(adj_off_eff, 130), 2),  # realistic ceiling
            "Adjusted Defensive Efficiency": round(min(adj_def_eff, 130), 2),  # ditto
            "Power Rating": round(power_rating, 2),
            "Effective FG% (Offense)": round(efg, 3),
            "Effective FG% (Defense)": round(efg_d, 3),
            "Turnover % (Offense)": round(tor, 3),
            "Turnover % (Defense)": round(tord, 3),
            "Offensive Rebound Rate": round(min(orb, 0.4), 3),  # max ~40%
            "Defensive Rebound Rate Allowed": round(min(drb_allowed, 0.4), 3),  # same
            "Free Throw Rate": round(ftr, 3),
            "Free Throw Rate Allowed": round(ftrd, 3),
            "Adjusted Tempo": round(min(tempo, 75), 2)  # cap tempo just slightly
        })
        flat_log.append(flat_game)
    return flat_log


def clear_screen(): #clears the screen to make the game look cleaner and more organized
    print("\n" * 75)

def generate_schedule(teams_df, user_team_conference, user_team): #schedules out of conference and conference games
    schedule = []
    out_of_conference_teams = teams_df[(teams_df['CONF'] != user_team_conference) & (teams_df['TEAM'] != user_team)]
    in_conference_teams = teams_df[(teams_df['CONF'] == user_team_conference) & (teams_df['TEAM'] != user_team)]

    for week in range(1, 8): #first 8 weeks are out of conference games
        if not out_of_conference_teams.empty: #appends teams to schedule if they are out of conference (randomly selected)
            random_team = out_of_conference_teams.sample(1).iloc[0]
            schedule.append({
                "week": week,
                "opponent": random_team['TEAM'],
                "conference": "Out-of-Conference",
                "overall_rating": determine_opponent_overall(random_team, teams_df),
            })
            out_of_conference_teams = out_of_conference_teams[out_of_conference_teams['TEAM'] != random_team['TEAM']]

    for week in range(8, 15): #in conference games
        if not in_conference_teams.empty:#appends teams to schedule if they are in conference (randomly selected)
            random_team = in_conference_teams.sample(1).iloc[0]
            schedule.append({
                "week": week,
                "opponent": random_team['TEAM'],
                "conference": f"In-Conference ({user_team_conference})",
                "overall_rating": determine_opponent_overall(random_team, teams_df),
            })
            in_conference_teams = in_conference_teams[in_conference_teams['TEAM'] != random_team['TEAM']]

    return schedule



# Function to load team data from Google Sheets and deal with the ssl verification
def load_team_data(api_link, year=None):
    ssl._create_default_https_context = ssl._create_unverified_context  # Removes SSL verification
    df = pd.read_csv(api_link)  # Read data from the CSV link
    if year:
        df = df[df['YEAR'] == year]  # Filter for the selected year
    return df

def view_team_statistics(): #able to view any team statistic from the previous year using the google sheet
    global selected_team, last_statistics_output
    clear_screen()
    teams_df = load_team_data(api_link, year=2023)
    teams_df['CONF'] = teams_df['CONF'].map(CONFERENCE_MAPPING).fillna(teams_df['CONF'])
    teams_df = teams_df[teams_df['YEAR'] == 2023]

    statistics = [
        "Team Name", "Conference", "Number of Games Played", "Number of Wins", "Adjusted Offensive Efficiency",
        "Adjusted Defensive Efficiency", "Power Rating", "Effective Field Goal Percentage (Offense)",
        "Effective Field Goal Percentage (Defense)", "Turnover Percentage (Offense)",
        "Turnover Percentage (Defense/Steal Rate)", "Offensive Rebound Rate",
        "Defensive Rebound Rate Allowed", "Free Throw Rate", "Free Throw Rate Allowed",
        "Two-Point Shooting Percentage", "Two-Point Shooting Percentage Allowed",
        "Three-Point Shooting Percentage", "Three-Point Shooting Percentage Allowed",
        "Adjusted Tempo", "Wins Above Bubble", "Postseason Outcome", "NCAA Tournament Seed"
    ] #remaps the name of the statistic to their actual names from the column abbreviations (just like conference mapping)
    columns = ['TEAM', 'CONF', 'G', 'W', 'ADJOE', 'ADJDE', 'BARTHAG', 'EFG_O', 'EFG_D', 'TOR', 'TORD', 'ORB', 'DRB',
               'FTR', 'FTRD', '2P_O', '2P_D', '3P_O', '3P_D', 'ADJ_T', 'WAB', 'POSTSEASON', 'SEED']

    print("\n--- View Team Statistics for 2023 ---")
    print("Available statistics:")
    for idx, stat in enumerate(statistics, start=1): #loops through all stat columns
        print(f"{idx}. {stat}")

    try:
        stat_choice_num = int(input("\nSelect a statistic by typing its number: ")) #users decision on what stat to look at
        if 1 <= stat_choice_num <= len(columns): #maps user number to associated column
            stat_choice = columns[stat_choice_num - 1]
            if stat_choice == 'SEED':
                teams_df[stat_choice] = teams_df[stat_choice].astype(int) #convert seed into integers
            sorted_df = teams_df[['TEAM', stat_choice]].sort_values(by=stat_choice, ascending=False) #sort teams by chosen stat
            if stat_choice in ['G', 'W', 'POSTSEASON', 'SEED']:
                stat_word = "played" if stat_choice == 'G' else "won" if stat_choice == 'W' else "was seeded"
            else:
                stat_word = "averages"
            user_team = sorted_df[sorted_df['TEAM'] == selected_team['TEAM']] #filters to users team
            output_lines = []
            if not user_team.empty:
                user_stat = user_team.iloc[0][stat_choice] #find user teams chosen stat
                if stat_choice in ['G', 'W', 'SEED']:
                    output_lines.append(f"\n{selected_team['TEAM']} {stat_word} {user_stat} for '{statistics[stat_choice_num - 1]}'.")
                else:
                    output_lines.append(f"\n{selected_team['TEAM']} {stat_word} {user_stat:.2f} for '{statistics[stat_choice_num - 1]}'.")
            output_lines.append(f"\nTop 10 teams for '{statistics[stat_choice_num - 1]}' last season:")
            top_10 = sorted_df.head(10) #find the top 10 for the chosen stat as well
            for rank, row in enumerate(top_10.iterrows(), start=1):
                if stat_choice == 'SEED':
                    output_lines.append(f"{rank}. {row[1]['TEAM']} was seeded {int(row[1][stat_choice])}")
                elif stat_choice in ['G', 'W']:
                    output_lines.append(f"{rank}. {row[1]['TEAM']} {stat_word} {int(row[1][stat_choice])}")
                else:
                    output_lines.append(f"{rank}. {row[1]['TEAM']} {stat_word} {row[1][stat_choice]:.2f}")
        else:
            output_lines = ["Invalid choice. Please select a valid number."]
    except ValueError:
        output_lines = ["Invalid input. Please enter a number."]

    final_output = "\n".join(output_lines) #puts all output lines of this function into a single string
    print(final_output)
    globals()['last_statistics_output'] = final_output #saves the last viewed statistic
    game_menu()

team_record = {"wins": 0, "losses": 0} #sets dictionary for user team record
last_week_matchup = None


def view_last_week_stats():
    if not game_log:
        print("\nNo games played yet.")
        input("Press Enter to return to the menu...")
        return

    last_game = game_log[-1]

    print(f"\n--- Last Week's Game Stats vs {last_game['opponent']} ---")
    print(
        f"Result: {last_game['result'].capitalize()} | Final Score: {last_game['team_score']} - {last_game['opponent_score']} ({last_game['period']})")

    print("\n-- Your Team's Stats --")
    for k, v in last_game['team_stats'].items():
        print(f"{k}: {v}")

    print("\n-- Opponent's Stats --")
    for k, v in last_game['opponent_stats'].items():
        print(f"{k}: {v}")

    print("\n-- Advanced Metrics --")
    flat = flatten_game_log([last_game])[0]
    advanced_keys = [
        "Adjusted Offensive Efficiency", "Adjusted Defensive Efficiency", "Power Rating",
        "Effective FG% (Offense)", "Effective FG% (Defense)", "Turnover % (Offense)",
        "Turnover % (Defense)", "Offensive Rebound Rate", "Defensive Rebound Rate Allowed",
        "Free Throw Rate", "Free Throw Rate Allowed", "Adjusted Tempo"
    ]
    for key in advanced_keys:
        print(f"{key}: {flat[key]}")

    input("\nPress Enter to return to the menu...")
    game_menu()

def generate_team_stats(score):
    possessions = random.randint(65, 72)
    fg_percentage = random.uniform(0.42, 0.51)
    fg_made = round(score * fg_percentage)
    fg_attempted = round(fg_made / fg_percentage)

    rebounds = random.randint(30, 42)
    assists = round(fg_made * random.uniform(0.5, 0.7))
    turnovers = random.randint(8, 15)
    free_throws_made = random.randint(10, 20)
    free_throws_attempted = round(free_throws_made / random.uniform(0.65, 0.78))

    # Advanced Metrics
    efg_off = round((fg_made + 0.5 * random.randint(3, 8)) / fg_attempted, 3)
    efg_off = min(efg_off, 0.58)

    to_percent = round(turnovers / possessions, 3)
    to_percent = max(min(to_percent, 0.22), 0.12)

    oreb_rate = round(random.uniform(0.22, 0.40), 3)
    ftr = round(free_throws_made / fg_attempted, 3)
    ftr = min(ftr, 0.35)

    adj_oe = round((score / possessions) * 100, 2)
    adj_oe = min(adj_oe, 130)

    return {
        "points": score,
        "FGM": fg_made,
        "FGA": fg_attempted,
        "REB": rebounds,
        "AST": assists,
        "TO": turnovers,
        "FTM": free_throws_made,
        "FTA": free_throws_attempted,
        "possessions": possessions,
        "adj_oe": adj_oe,
        "efg_off": efg_off,
        "to_percent": to_percent,
        "oreb_rate": oreb_rate,
        "ftr": ftr
    }


def simulate_game(team_overall, opponent_overall):
    def generate_score(base_overall, is_user_team=False):
        base_score = random.randint(65, 90) + int((base_overall - 60) * 0.5)  #starts by generating a random score for the user. then adds the user's overall to scale the score value on how good they are
        variability = random.randint(-15, 15) if is_user_team else random.randint(-20, 20) #generates a randint variability factor that slightly affects game scores
        adjusted_score = base_score + variability #adds the variability to the original generated score
        if not is_user_team and base_overall < 70:
            adjusted_score += random.randint(-10, 10) #if a team is extra bad (under 70 overall) they get even more variability on their score to encourage blowouts
        return max(50, min(adjusted_score, 110)) #min of 50 pts scored, max of 110pts
    team_overall += random.randint(7, 12) # difficulty slider, add higher values for easier simulation Difficulties:(EASY: 7,12. NORMAL: 6,10. HARD: 4,8)
    team_score = generate_score(team_overall, is_user_team=True)
    opponent_score = generate_score(opponent_overall)
    if abs(team_score - opponent_score) > 15: #if blowout by 15pts, slims the gap just a bit to force closer games
        adjustment = random.randint(-5, 5)
        team_score += adjustment
        opponent_score -= adjustment
    overtime = False
    while team_score == opponent_score: #if the game is generated with a tie, each team will get a random added value to see who wins
        overtime = True
        team_score += random.randint(5, 15)
        opponent_score += random.randint(5, 15)
    win = team_score > opponent_score
    outcome = "win" if win else "loss" #produces what the true outcome was
    period = "OT" if overtime else "regulation" #says OT or regulation based on if the game went into OT or not
    team_stats = generate_team_stats(team_score)
    opponent_stats = generate_team_stats(opponent_score)
    return {
        "team_score": team_score,
        "opponent_score": opponent_score,
        "outcome": outcome,
        "period": period,
        "team_stats": team_stats,
        "opponent_stats": opponent_stats
    }




#User picks a team
def pick_team(teams_df):
    team_name = input("Enter the name of your college basketball team: ").strip()
    matching_team = teams_df[teams_df['TEAM'].str.lower() == team_name.lower()] #lower ensures no capitalization issues when picking a team

    if not matching_team.empty: #checks if matching teams dataframe is empty
        selected_team = matching_team.iloc[0] #selects first row from matching_teams
        wins = selected_team['W'] #shows the teams stats
        games_played = selected_team['G'] #^
        losses = games_played - wins
        record = f"{wins}-{losses}" #^

#same with the conference mapping, this fixes abbreviations from the database
        postseason_mapping = {
            'champions': 'Champion',
            '2nd': 'Runner-up',
            'f4': 'Final Four',
            'e8': 'Elite Eight',
            's16': 'Sweet 16',
            'r32': 'Round of 32',
            'r64': 'Round of 64',
            'na': 'No Appearance'
        }
        postseason = str(selected_team['POSTSEASON']).lower() if pd.notna(selected_team['POSTSEASON']) else 'na' #creates a lowercase outcome of the postseason or says NA if team didnt make it last year
        postseason_full = postseason_mapping.get(postseason, postseason)

        return selected_team
    else:
        print(f"Team '{team_name}' not found. Please try again.")
        return pick_team(teams_df)

#generate a hidden potential statistic that will be reached by their peak (end of senior year)
def generate_hidden_potential(age):
    if age <= 22:
        return random.randint(80, 99)  # Higher potential for younger players
    else:
        return random.randint(70, 90)  # Lower potential for older players (less time to reach their top potential)

#generate individual player overall
def generate_attributes_based_on_potential(potential, age, experience_years):
    adjustment_factor = experience_years * 2  # more experience means higher attributes

    if age == 18:  # Recruits start at 18, lower raw stats but higher potential
        base_value = potential * 0.7  # Start at 70% of potential for freshmen
    else:
        base_value = potential * 0.75 + adjustment_factor  # Start at 75% of potential for experienced players

    # Weighted distribution to make 50% of the stats fall between 75-85
    def adjust_stat(base_value):
        if random.random() < 0.5:  # 50% chance for a stat between 75-85
            raw_value = random.randint(75, 85)
        else:  # Other 50% chance for a stat between 65-95 (much wider range of attributes)
            raw_value = random.randint(65, 95)
        adjustment = random.randint(-5, 5)
        raw_value += adjustment #adds variability by randomizing the values added
        return min(99, max(60, round(raw_value))) #puts a max on attributes)

    return {
        'Shooting': adjust_stat(base_value),
        'Close Shot': adjust_stat(base_value),
        'Defense': adjust_stat(base_value),
        'Dribbling': adjust_stat(base_value),
        'Passing': adjust_stat(base_value),
        'Rebounding': adjust_stat(base_value),
        'Athletic Ability': adjust_stat(base_value),
    } #return all player stats

def calculate_overall(player): #function to calculate overall average (average of all stats)
    return round((player['Shooting'] + player['Close Shot'] + player['Defense'] +
                  player['Dribbling'] + player['Passing'] + player['Athletic Ability']) / 6)

def main_menu(): #main menu options
    clear_screen()
    print("\nWelcome to the College Basketball Coach Simulator")
    print("1. Start New Game")
    print("2. Load Game")
    print("3. Quit")
    choice = input("Select an option: ")

    if choice == "1":
        start_new_game()
    elif choice == "2":
        load_game()
    elif choice == "3":
        quit_game()
    else:
        print("Invalid choice. Please select again.")
        main_menu()

# Function to quit the game
def quit_game():
    print("\nExiting the game. Goodbye!")
    exit()


def start_new_game():
    global current_year, current_week, scouting_points, recruiting_points, schedule, selected_team
    current_year = 2024
    current_week = 0
    scouting_points = 3
    recruiting_points = 5

    print(f"\nStarting a new game... Year {current_year} Week {current_week}") #shows current year/week
    coach_name = input("Enter your coach's name: ") #user input

    teams_df = load_team_data(api_link, year=2023) #makes sure the previous data is loaded from the last year (2023 is the final column in the dataset)
    selected_team = pick_team(teams_df)
    if selected_team is not None:
        selected_team_conference = selected_team['CONF']
        full_conference_name = CONFERENCE_MAPPING.get(selected_team_conference, selected_team_conference)

        wins = selected_team['W']
        games_played = selected_team['G']
        losses = games_played - wins
        record = f"{wins}-{losses}"

        postseason_mapping = {
            'champions': 'Champion',
            '2nd': 'Runner-up',
            'f4': 'Final Four',
            'e8': 'Elite Eight',
            's16': 'Sweet 16',
            'r32': 'Round of 32',
            'r64': 'Round of 64',
            'na': 'No Appearance'
        }

        postseason = str(selected_team['POSTSEASON']).lower()
        postseason_full = postseason_mapping.get(postseason, postseason)

        user_team_info.update({
            "school": selected_team['TEAM'],
            "conference": full_conference_name,
            "coach_name": coach_name,
            "record": record
        })

        print(f"\nYou are coaching: {selected_team['TEAM']}")
        print(f"Conference: {full_conference_name}")
        print(f"Last Year's Record: {record}")
        print(f"Postseason Success: {postseason_full}")
        print(f"Welcome, Coach {coach_name}! You are now the head coach of the {selected_team['TEAM']}.")

        generate_team()
        generate_recruits()
        schedule = generate_schedule(teams_df, full_conference_name, selected_team['TEAM'])
        game_menu()
    else:
        print("Team not found. Returning to the main menu.")
        main_menu()

# Placeholder for loading a game (doesnt actually work, i'm not sure how to save data after ending the game)
def load_game():
    print("\nLoading an existing game... (Feature to be added later)")
    main_menu()

# 2. Team Generation and Initial Setup
def generate_random_height(position):

        if position == 'PG':  # Point Guard heights with weighted average, most should fall between 6'0 - 6'2 and total ranges from 5'7 to 6'5
            height_ranges = [(5, 7), (5, 8), (5, 9), (5, 10), (5, 11), (6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (6, 5)]
            weights = [2, 3, 4, 5, 6, 12, 25, 25, 10, 5, 3]
        elif position == 'SG':  # Shooting Guard with average sitting between 6'3 to 6'5 and total range from 6'1 to 6'8
            height_ranges = [(6, 1), (6, 2), (6, 3), (6, 4), (6, 5), (6, 6), (6, 7), (6, 8)]
            weights = [10, 15, 25, 20, 15, 10, 3, 2]
        elif position == 'SF':  # Small Forward heights with weighted average, most should fall between 6'6-6'8 and total range from 6'4 to 6'11
            height_ranges = [(6, 4), (6, 5), (6, 6), (6, 7), (6, 8), (6, 9), (6, 10), (6, 11)]
            weights = [5, 8, 20, 25, 20, 12, 7, 3]
        elif position == 'PF':  # Power Forward heights with weighted average, most fall between 6'9 to 6'11 with total range from 6'7 to 7'1
            height_ranges = [(6, 7), (6, 8), (6, 9), (6, 10), (6, 11), (7, 0), (7, 1)]
            weights = [5, 10, 20, 25, 20, 15, 5]
        elif position == 'C':  # Center height with weighted average, most fall between 6'10 and 7'1 with total range from 6'8 to 7'6
            height_ranges = [(6, 8), (6, 9), (6, 10), (6, 11), (7, 0), (7, 1), (7, 2), (7, 3), (7, 4), (7, 5), (7, 6)]
            weights = [2, 5, 10, 25, 20, 15, 10, 5, 3, 2, 1]

        # Randomly pick a height based on the weighted distribution
        feet, inches = random.choices(height_ranges, weights=weights)[0]
        return f"{feet}'{inches}\""


#generate players for team management (NOT RECRUIT GENERATION, 2 DIFFERENT THINGS)
def generate_player(position, stat_range, height, experience_years):
    age = random.randint(18, 22)  # Players will have age between 18 and 22
    potential = generate_hidden_potential(age)
    attributes = generate_attributes_based_on_potential(potential, age, experience_years)  # Use experience/adjustment factor

    player = {
        'Position': position,
        'Shooting': attributes['Shooting'],
        'Close Shot': attributes['Close Shot'],
        'Defense': attributes['Defense'],
        'Dribbling': attributes['Dribbling'],
        'Passing': attributes['Passing'],
        'Rebounding': attributes['Rebounding'],
        'Athletic Ability': attributes['Athletic Ability'],
        'Height': height,
        'Potential': potential,
        'Age': age,
        'Experience': experience_years,
        'Overall': calculate_overall(attributes)
    }
    return player

#generate team based off of generate player function
def generate_team():
    global team
    team = []
    positions = ['PG', 'SG', 'SF', 'PF', 'C']
    team_conference = selected_team['CONF']

    team.append(generate_player_with_name('PG', (74, 92), team_conference)) #creates a player for each position (starting 5)
    team.append(generate_player_with_name('SG', (74, 92), team_conference))
    team.append(generate_player_with_name('SF', (74, 92), team_conference))
    team.append(generate_player_with_name('PF', (74, 92), team_conference))
    team.append(generate_player_with_name('C', (74, 92), team_conference))

    team.append(generate_player_with_name(random.choice(positions), (65, 85), team_conference)) #3 bench players with 1 really solid 6th man
    team.append(generate_player_with_name(random.choice(positions), (60, 80), team_conference))
    team.append(generate_player_with_name(random.choice(positions), (60, 80), team_conference))

#
def assign_position_by_height(height): #cleans up height string to deal with the apostrophe
    feet, inches = map(int, height.replace('"', '').split("'"))
    total_inches = feet * 12 + inches #converts to total inches to help with assigning positions
    if 67 <= total_inches <= 77:  # PG: 5'7" to 6'5"
        return random.choices(['PG', 'SG'], weights=[80, 20])[0]
    elif 73 <= total_inches <= 80:  # SG: 6'1" to 6'8"
        return random.choices(['SG', 'SF'], weights=[60, 40])[0]
    elif 76 <= total_inches <= 83:  # SF: 6'4" to 6'11"
        return random.choices(['SF', 'PF'], weights=[60, 40])[0]
    elif 79 <= total_inches <= 85:  # PF: 6'7" to 7'1"
        return random.choices(['PF', 'C'], weights=[60, 40])[0]
    else:  # C: 6'8" to 7'6"
        return 'C'


def generate_player_with_name(position, stat_range, team_conference=None):
    age = random.choices([18, 19, 20, 21, 22], weights=[10, 25, 25, 25, 15])[0]
    experience_years = age - 18 #years of experience in college
    potential = generate_hidden_potential(age)
    if team_conference in {'SEC', 'ACC', 'Big 12', 'Big East', 'WCC (Gonzaga)'}:
        potential = max(potential, random.randint(85, 99)) #if a team is in a top conference or is Gonzaga (not user), then they are automatically above an 85 overall to make realistic skill levels between conferences
    else:
        potential = min(potential, random.randint(65, 85)) #regular team overalls
    attributes = generate_attributes_based_on_potential(potential, age, experience_years)
    player = {
        'Name': generate_random_name(),
        'Age': age,
        'Class': assign_class(age),
        'Potential': potential,
        'Height': generate_random_height(position),
        'Primary Position': position,
        'Overall': calculate_overall(attributes),
        'Interest': random.randint(0, 100),
        'Scouted': False,
        'revealed_stats': [],
        **attributes
    }
    return player

def assign_class(age): #assigns class based on generated age
    if age == 18:
        return 'Freshman'
    elif age == 19:
        return 'Sophomore'
    elif age == 20:
        return 'Junior'
    elif age == 21:
        return 'Senior'
    else:
        return 'Redshirt Senior'

#found a random list of first names in US directory
def generate_random_name():
    first_names = [
        'John', 'Michael', 'Chris', 'Kyle', 'Jordan', 'David', 'James', 'Brian', 'Mark', 'Kevin',
        'Andrew', 'Matthew', 'Justin', 'Eric', 'Ryan', 'Daniel', 'Jason', 'Aaron', 'Thomas', 'Robert',
        'Patrick', 'Alex', 'Tyler', 'Timothy', 'Adam', 'Scott', 'Sean', 'Brandon', 'Zachary', 'Jeffrey',
        'Nathan', 'Benjamin', 'Paul', 'Anthony', 'Steven', 'Gregory', 'Jack', 'Sam', 'Derek', 'Luke',
        'Jake', 'Oscar', 'Luis', 'Ricardo', 'Diego', 'Carlos', 'Eduardo', 'Hector', 'Alejandro',
        'Miguel', 'Santiago', 'Jorge', 'Manuel', 'Pedro', 'Tomas', 'Mateo', 'Lucas', 'Pablo', 'Rafael',
        'Raul', 'Giovanni', 'Luca', 'Angelo', 'Marco', 'Alessandro', 'Fabio', 'Nico', 'Lorenzo',
        'Stefano', 'Enrico', 'Mario', 'Leonardo', 'Matteo', 'Thiago', 'Felipe', 'Jose', 'Juan',
        'Esteban', 'Sergio', 'Andres', 'Francisco', 'Bruno', 'Emilio', 'Ramon', 'Enrique', 'Javier',
        'Ivan', 'Max', 'Elijah', 'Jackson', 'Ethan', 'Noah', 'Logan', 'Aiden', 'Henry', 'Sebastian',
        'Carter', 'Wyatt', 'Hunter', 'Isaiah', 'Caleb', 'Landon', 'Levi', 'Asher', 'Gavin', 'Tanner',
        'Declan', 'Oliver', 'Mason', 'Dylan', 'Owen', 'Blake', 'Jace', 'Jonah', 'Zane', 'Brody',
        'Axel', 'Cameron', 'Bennett', 'Elliot', 'Silas', 'Finley', 'Theo', 'Damian', 'Rowan', 'Finn',
        'Elijah', 'William', 'Mason', 'Logan', 'Oliver', 'Jayden', 'Connor', 'Julian', 'Nathaniel',
        'Carson', 'Sebastian', 'Samuel', 'Cooper', 'Hudson', 'Dominic', 'Braxton', 'Harrison', 'Roman',
        'Lincoln', 'Weston', 'Xavier', 'Miles', 'Parker', 'Easton', 'Beau', 'Ezra', 'Chase', 'Emmett',
        'Ryder', 'Spencer', 'Marcus', 'Vincent', 'Barrett', 'Camden', 'Maxwell', 'Colton', 'Finnegan',
        'Ashton', 'Silas', 'Porter', 'Mateo', 'Tristan', 'Wesley', 'Everett', 'Kai', 'Riley', 'Bodhi',
        'Dante', 'Remy', 'Cruz', 'Archer', 'Reid', 'Dawson', 'Luca', 'Jasper', 'Brock', 'Quinn', 'Troy',
        'Jett', 'Kingston', 'Holden', 'Reece', 'Jaden', 'Lachlan', 'Beckett', 'Kane', 'Zander', 'Ronan',
        'Tate', 'Gideon', 'Hugo', 'Rory', 'Sterling', 'Emery', 'Sullivan', 'Milo', 'Franklin', 'Pierce',
        'Hendrix', 'Orion', 'Dalton', 'Phoenix', 'Nash', 'Clayton', 'Dallas', 'Grady', 'Sterling', 'Atlas',
        'Malik', 'Darius', 'Jamal', 'Tyrone', 'Kareem', 'Rashad', 'Jalen', 'DeAndre', 'Deshawn', 'Lamar',
        'Trevon', 'Marquis', 'Devonte', 'Jerome', 'Terrence', 'Demarcus', 'Antwan', 'Javon', 'Darnell', 'Tariq',
        'Kwame', 'Marquez', 'Andre', 'Khalil', 'Keon', 'Tyrell', 'Jabari', 'Rasheed', 'Montel', 'DeMarcus',
        'Maurice', 'Tavon', 'Deon', 'Isaiah', 'Tyriek', 'Corey', 'Dominique', 'Donnell', 'Ahmad', 'Marcellus',
        'Daquan', 'Xavier', 'Jamar', 'Kendrick', 'Shaquan', 'Quincy', 'Zaire', 'Marvin', 'Nasir', 'Amir',
        'Keenan', 'Travon', 'Malcolm', 'Desmond', 'Hakim', 'Alonzo', 'Donnell', 'Raheem', 'Demonte', 'Javonte',
        'Tyree', 'LeBron', 'Juwan', 'Kanye', 'Kobe', 'Tyran', 'Jaleel', 'Trey', 'DeShawn', 'Jaheim', 'Myron',
        'Damien', 'Kadeem', 'Trayvon', 'Jaden', 'Demetrius', 'Keenon', 'Latrell', 'Taj', 'Cortez', 'Jahlil',
        'Keshawn', 'Elijah', 'Khalid', 'Jamil', 'Quadir', 'Malachi', 'Romello', 'Tyrik', 'DeVante', 'Malik',
        'Denzel', 'Jalen', 'Quenton', 'Devon', 'Marquise', 'Shaun', 'Tyshawn', 'Keonte', 'Akil', 'Tyrice'
    ]
#random list of last names in the US directory
    last_names = [
        'Smith', 'Johnson', 'Brown', 'Williams', 'Jones', 'Garcia', 'Miller', 'Davis', 'Martinez',
        'Wilson', 'Anderson', 'Taylor', 'Thomas', 'Moore', 'Jackson', 'White', 'Harris', 'Martin',
        'Thompson', 'Martinez', 'Robinson', 'Clark', 'Rodriguez', 'Lewis', 'Lee', 'Walker', 'Hall',
        'Allen', 'Young', 'Hernandez', 'King', 'Wright', 'Lopez', 'Hill', 'Scott', 'Green', 'Adams',
        'Baker', 'Gonzalez', 'Nelson', 'Carter', 'Mitchell', 'Perez', 'Roberts', 'Turner', 'Phillips',
        'Campbell', 'Parker', 'Evans', 'Edwards', 'Collins', 'Stewart', 'Sanchez', 'Morris', 'Rogers',
        'Reed', 'Cook', 'Morgan', 'Bell', 'Murphy', 'Bailey', 'Rivera', 'Cooper', 'Richardson',
        'Cox', 'Howard', 'Ward', 'Torres', 'Peterson', 'Gray', 'Ramirez', 'James', 'Watson',
        'Brooks', 'Kelly', 'Sanders', 'Price', 'Bennett', 'Wood', 'Barnes', 'Ross', 'Henderson',
        'Coleman', 'Jenkins', 'Perry', 'Powell', 'Long', 'Patterson', 'Hughes', 'Flores', 'Washington',
        'Butler', 'Simmons', 'Foster', 'Gonzales', 'Bryant', 'Alexander', 'Russell', 'Griffin', 'Diaz',
        'Montgomery', 'Porter', 'Mendoza', 'Silva', 'Cross', 'Fleming', 'Holt', 'Cunningham', 'Palmer',
        'Lawson', 'Reyes', 'Tucker', 'Watts', 'Bishop', 'Hawkins', 'Lowe', 'Fisher', 'Graves', 'Hayes',
        'Stewart', 'Owens', 'McCarthy', 'Holland', 'Duncan', 'Barrett', 'Parker', 'Frank', 'Newton',
        'Warner', 'Armstrong', 'Schultz', 'Lane', 'Nixon', 'Booth', 'Wilkins', 'Curtis', 'Hubbard',
        'Owens', 'Hardy', 'Snyder', 'Fletcher', 'Ross', 'Graham', 'Murray', 'Bates', 'Gregory',
        'Pittman', 'Wilkerson', 'Shelton', 'Burgess', 'Reeves', 'Underwood', 'Wallace', 'Stevens',
        'Simpson', 'Blair', 'Patrick', 'Mathis', 'Floyd', 'Beasley', 'Vargas', 'Steele', 'Lucas',
        'Love', 'Snow', 'Robbins', 'Hamilton', 'Phelps', 'Fitzgerald', 'Levy', 'Ramsey', 'Brewer'
    ]
    return f"{random.choice(first_names)} {random.choice(last_names)}"


#generate top 25 recruits and randomized interest level
def generate_recruits():
    global recruits
    recruits = []
    for i in range(25):
        age = 18
        potential = generate_hidden_potential(age)
        position = random.choice(['PG', 'SG', 'SF', 'PF', 'C'])
        attributes = generate_attributes_based_on_potential(potential, age, 0)
        recruit = {
            'ID': i,
            'Name': generate_random_name(),
            'Age': age,
            'Class': 'Freshman',
            'Potential': potential,
            'Height': generate_random_height(position),
            'Primary Position': position,
            'Overall': calculate_overall(attributes),
            'Interest': random.randint(0, 100),
            'Scouted': False,
            'revealed_stats': [],
            **attributes
        }
        recruits.append(recruit)


def display_user_team_info(): #displays the users main info every week (coach name, team name, conference, last yrs record
    if user_team_info["school"]:
        print(f"\n--- {user_team_info['school']} ({user_team_info['conference']}) ---")
        print(f"Coach: {user_team_info['coach_name']} | Last Year's Record: {user_team_info['record']}")
    else:
        print("\nNo team selected yet.")

def game_menu():
    global next_matchup, last_week_matchup, committed_recruit_messages, tournament_messages, last_statistics_output, offseason_messages
    clear_screen()

    if offseason_messages: #shows after the clear_screen function
        for msg in offseason_messages:
            print(msg)
        offseason_messages.clear()

    for message in tournament_messages: #shows after the clear_screen function
        print(message)
    tournament_messages.clear()

    display_user_team_info()

    if last_statistics_output: #shows after the clear_screen function
        print(last_statistics_output)
        last_statistics_output = ""

    print(f"\n--- Year {current_year} Week {current_week} ---")
    print(f"Current Record: {team_record['wins']}-{team_record['losses']}")

    if committed_recruit_messages: #shows after the clear_screen function
        for message in committed_recruit_messages:
            print(f"\n{message}")

    if last_week_matchup and "message" not in last_week_matchup: #Prints last week's matchup's results including standout player stats as well
        print(f"\nLast week's matchup against {last_week_matchup['opponent']} resulted in a {last_week_matchup['result']}.")
        print(f"The final score was {last_week_matchup['score']} in {last_week_matchup['period']}.")
        if "stat_line" in last_week_matchup:
            eligible_players = [p for p in team if not p.get('Redshirted', False)] #ensures no redshirted players can be a player of the game as they arn't playing that year
            if eligible_players:
                random_player = random.choice(eligible_players)
                print(f"A standout performance came from {random_player['Name']} with a stat line of {last_week_matchup['stat_line']}.")
    else:
        print("\nLast week's matchup: No games played last week.") #if no games played the week b4

    if next_matchup: #shows preview of the upcoming matchup
        print(f"\n--- Next Week's Matchup (Week {current_week + 1}) ---")
        print(f"Opponent: {next_matchup['opponent']}")
        print(f"Conference: {next_matchup['conference']}")
        print(f"Overall Team Rating: {next_matchup['overall_rating']}")
    else:
        print("\nNo upcoming matchup scheduled.")

    print("\n--- Game Menu ---")
    print("1. Advance Week (Simulate Recruiting)")
    print("2. Recruiting Menu")
    print("3. Current Team Management")
    print("4. View Team Statistics (2024)")
    print("5. View Last Week's Full Team Stats")
    print("6. Quit")

    choice = input("Select an option: ").strip()
    full_width_map = {
        '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
        '５': '5', '６': '6', '７': '7', '８': '8', '９': '9'
    }
    normalized_choice = "".join(full_width_map.get(ch, ch) for ch in choice) #used chatgpt to understand what the ASCII stuff is and why a full-width map converts user inputs better

    if normalized_choice == "1":
        teams_df = load_team_data(api_link, year=2023)
        advance_week(teams_df)
        game_menu()
    elif normalized_choice == "2":
        recruit_menu()
        game_menu()
    elif normalized_choice == "3":
        current_team_management()
        game_menu()
    elif normalized_choice == "4":
        view_team_statistics()
    elif normalized_choice == "5":
        view_last_week_stats()
    elif normalized_choice == "6":
        quit_game()

    else:
        print("\nInvalid choice. Please select again.")
        game_menu()

def determine_opponent_overall(team_row, teams_df):
    power_rating = team_row['BARTHAG']
    base_overall = (power_rating - teams_df['BARTHAG'].min()) / (teams_df['BARTHAG'].max() - teams_df['BARTHAG'].min()) #based on their power rankings from their 2023 stats in the dataset
    overall = int(base_overall * 39 + 60)  # Scaled to fit 60-99 range
    overall += np.random.randint(-5, -1)  # Randomized adjustment
    overall -= np.random.randint(2, 4)  # Difficulty adjustment
    overall = max(60, min(overall, 99))  # Clamped to 60-99
    return overall

#sets matchup for upcoming week
def announce_upcoming_matchup(week, teams_df):
    global selected_team, next_matchup, scheduled_opponents

    display_week = week + 1 #ensures upcoming matchup is 1 week ahead of current week

    if display_week == 0:
        print("\nNo games this week. It is the offseason/preseason.")
        return
    if 1 <= display_week <= 7:
        opponents_df = teams_df[(teams_df['CONF'] != selected_team['CONF']) & (teams_df['TEAM'] != selected_team['TEAM'])]
        conference_type = "Out-of-Conference"
    elif 8 <= display_week <= 14:
        opponents_df = teams_df[(teams_df['CONF'] == selected_team['CONF']) & (teams_df['TEAM'] != selected_team['TEAM'])]
        conference_type = f"In-Conference ({selected_team['CONF']})"
    else:
        next_matchup = None
        print("\nNo more scheduled games. The season has ended.")
        return

    opponents_df = opponents_df[~opponents_df['TEAM'].isin(scheduled_opponents)] #filters to exclude previously played teams
    if not opponents_df.empty:
        opponent = opponents_df.sample(1).iloc[0] #selects random opponent
        opponent_name = opponent['TEAM']
        opponent_overall = determine_opponent_overall(opponent, teams_df)
        next_matchup = {
            "week": week,
            "opponent": opponent_name,
            "conference": conference_type,
            "overall_rating": opponent_overall
        }
        scheduled_opponents.add(opponent_name) #track scheduled opponents
    else:
        next_matchup = None
        print(f"No {conference_type.lower()} teams available for selection.")

def handle_player_progression():
    global team
    new_team = []
    for player in team:
        base_class = player['Class']
        redshirted = player.get('Redshirted', False)
        player['Redshirted'] = False
        age = player['Age']
        if base_class == 'Senior' or base_class == 'Redshirt Senior': #player graduates if they are a senior or played their redshirt senior yr.
            if base_class == 'Senior' and not redshirted:
                continue
            if base_class == 'Senior' and redshirted:
                player['Class'] = 'Redshirt Senior'
            elif base_class == 'Redshirt Senior':
                continue
        else:
            if redshirted: #changes class name after season is over
                if base_class == 'Freshman':
                    player['Class'] = 'Redshirt Freshman'
                elif base_class == 'Sophomore':
                    player['Class'] = 'Redshirt Sophomore'
                elif base_class == 'Junior':
                    player['Class'] = 'Redshirt Junior'
                elif base_class == 'Senior':
                    player['Class'] = 'Redshirt Senior'
            else:
                if base_class == 'Freshman':
                    player['Class'] = 'Sophomore'
                elif base_class == 'Sophomore':
                    player['Class'] = 'Junior'
                elif base_class == 'Junior':
                    player['Class'] = 'Senior'
                elif base_class == 'Redshirt Freshman':
                    player['Class'] = 'Sophomore'
                elif base_class == 'Redshirt Sophomore':
                    player['Class'] = 'Junior'
                elif base_class == 'Redshirt Junior':
                    player['Class'] = 'Senior'
        if player['Class'] in ['Redshirt Freshman', 'Redshirt Sophomore', 'Redshirt Junior']:
            player['Age'] += 1 #if generated player has a preset redshirt, make their age 1 ahead
        elif player['Class'] == 'Senior' or player['Class'] == 'Redshirt Senior':
            if player['Class'] == 'Redshirt Senior':
                player['Age'] += 1
            else:
                player['Age'] += 1
        else:
            player['Age'] += 1
        if player['Class'] not in ['Redshirt Senior'] and not (player['Class'] == 'Senior' and not redshirted): #every statistic is increased by 2 to 5 at the end of the year to show progression
            increment = lambda: random.randint(2, 5)
            player['Shooting'] = min(player['Shooting'] + increment(), 99)
            player['Close Shot'] = min(player['Close Shot'] + increment(), 99)
            player['Defense'] = min(player['Defense'] + increment(), 99)
            player['Dribbling'] = min(player['Dribbling'] + increment(), 99)
            player['Passing'] = min(player['Passing'] + increment(), 99)
            player['Rebounding'] = min(player['Rebounding'] + increment(), 99)
            player['Athletic Ability'] = min(player['Athletic Ability'] + increment(), 99)
            player['Overall'] = calculate_overall(player)
            new_team.append(player)
        else:
            if player['Class'] == 'Redshirt Senior':
                continue
            else:
                new_team.append(player)
    team = new_team


def start_next_tournament_round(): #only have good teams in the NCAA tournament (I couldn't figure out how to create a selection day type of simulation)
    global next_matchup, current_week
    HARD_CODED_TEAMS = [
        "Duke", "Clemson", "Pittsburgh", "SMU", "North Carolina",
        "Louisville", "Stanford", "Florida St.", "NC State", "Notre Dame",
        "Cal", "Wake Forest", "Virginia", "Syracuse", "Georgia Tech",
        "Miami FL", "Boston College", "Virginia Tech", "Dayton", "Davidson",
        "Houston", "Iowa St.", "Kansas", "Baylor", "Cincinnati",
        "Texas Tech", "Arizona St.", "Arizona", "West Virginia", "BYU",
        "Utah", "Colorado", "Oklahoma", "Oklahoma St.", "UCF",
        "TCU", "Kansas St.", "Marquette", "UConn", "St. John's",
        "Butler", "Villanova", "DePaul", "Creighton", "Providence",
        "Xavier", "Georgetown", "Seton Hall", "Illinois", "Maryland",
        "UCLA", "Oregon", "Penn St.", "Ohio St.", "Michigan",
        "Purdue", "Michigan St.", "Wisconsin", "Iowa", "Indiana",
        "Northwestern", "Nebraska", "Rutgers", "Washington", "USC",
        "Minnesota", "San Diego St.", "Nevada", "New Mexico", "Colorado St.",
        "UNLV", "Tennessee", "Auburn", "Kentucky", "Florida",
        "Alabama", "Georgia", "Ole Miss", "Texas A&M", "Missouri",
        "Arkansas", "Vanderbilt", "Texas", "South Carolina",
        "James Madison", "Memphis", "Florida Atlantic", "South Florida",
        "Saint Mary's", "San Francisco", "Oregon St.", "Washington St."
    ]

    tournament_rounds = [
        "Round of 64",
        "Round of 32",
        "Sweet 16",
        "Elite Eight",
        "Final Four",
        "Championship",
    ]
    if not next_matchup:
        print("No ongoing tournament matchup to progress.")
        return
    current_round_index = tournament_rounds.index(next_matchup["round"]) #shows upcoming round and matchup
    if current_round_index < len(tournament_rounds) - 1:
        next_round = tournament_rounds[current_round_index + 1]
        opponent_name = random.choice(HARD_CODED_TEAMS)
        next_matchup = {
            "week": current_week + 1,
            "opponent": opponent_name,
            "conference": "NCAA Tournament",
            "overall_rating": random.randint(80, 99),
            "round": next_round,
        }
    else:
        print("\n--- Congratulations! You have won the NCAA Championship! ---") #if win every round
        next_matchup = None


def prepare_tournament_matchup():
    global next_matchup
    HARD_CODED_TEAMS = [
        "Duke", "Clemson", "Pittsburgh", "SMU", "North Carolina",
        "Louisville", "Stanford", "Florida St.", "NC State", "Notre Dame",
        "Cal", "Wake Forest", "Virginia", "Syracuse", "Georgia Tech",
        "Miami FL", "Boston College", "Virginia Tech", "Dayton", "Davidson",
        "Houston", "Iowa St.", "Kansas", "Baylor", "Cincinnati",
        "Texas Tech", "Arizona St.", "Arizona", "West Virginia", "BYU",
        "Utah", "Colorado", "Oklahoma", "Oklahoma St.", "UCF",
        "TCU", "Kansas St.", "Marquette", "UConn", "St. John's",
        "Butler", "Villanova", "DePaul", "Creighton", "Providence",
        "Xavier", "Georgetown", "Seton Hall", "Illinois", "Maryland",
        "UCLA", "Oregon", "Penn St.", "Ohio St.", "Michigan",
        "Purdue", "Michigan St.", "Wisconsin", "Iowa", "Indiana",
        "Northwestern", "Nebraska", "Rutgers", "Washington", "USC",
        "Minnesota", "San Diego St.", "Nevada", "New Mexico", "Colorado St.",
        "UNLV", "Tennessee", "Auburn", "Kentucky", "Florida",
        "Alabama", "Georgia", "Ole Miss", "Texas A&M", "Missouri",
        "Arkansas", "Vanderbilt", "Texas", "South Carolina",
        "James Madison", "Memphis", "Florida Atlantic", "South Florida",
        "Saint Mary's", "San Francisco", "Oregon St.", "Washington St."
    ]
    opponent_name = random.choice(HARD_CODED_TEAMS)
    next_matchup = {
        "week": 16,
        "opponent": opponent_name,
        "conference": "NCAA Tournament",
        "overall_rating": random.randint(80, 99),
        "round": "Round of 64",
    }
    return next_matchup




def advance_week(teams_df):
    global current_week, current_year, scouting_points, recruiting_points, schedule, team_record
    global next_matchup, committed_recruits, last_week_matchup, committed_recruit_messages, tournament_messages

    committed_recruit_messages = []
    for recruit in recruits[:]:
        if recruit['Interest'] == 100 and recruit.get('scholarship_offered', False):
            if current_week == 0:
                message = f"{recruit['Name']} has committed to your team and is available this season."
                committed_recruit_messages.append(message)
                team.append(recruit)
            else:
                message = f"{recruit['Name']} has committed and will join the team next season."
                committed_recruit_messages.append(message)
                committed_recruits.append(recruit)
            recruits.remove(recruit)

    if current_week == 15:
        tournament_messages.append(f"--- Regular Season Ended ---")
        if team_record['wins'] >= 7:
            tournament_messages.append(f"Your team qualified for the NCAA Tournament with a record of {team_record['wins']}-{team_record['losses']}!")
            prepare_tournament_matchup()
            tournament_messages.append("--- NCAA Tournament Begins ---")
            if next_matchup:
                tournament_messages.append(f"Your team is ready! Opponent: {next_matchup['opponent']} (Overall: {next_matchup['overall_rating']})")
        else:
            tournament_messages.append(f"Your team did not qualify for the NCAA Tournament. Simulating through the tournament.")
        current_week += 1
        return

    if current_week >= 16 and next_matchup:
        team_overall = sum([player['Overall'] for player in team]) // len(team) + random.randint(4, 6)
        game_result = simulate_game(team_overall, next_matchup['overall_rating'])
        if game_result["outcome"] == "win":
            tournament_messages.append("Your team advances to the next round!")
            team_record["wins"] += 1
            start_next_tournament_round()
        else:
            tournament_messages.append(
                f"Your team was eliminated in the {next_matchup['conference']}. Please simulate past Week 25 to start a new season!"
            )
            last_week_matchup = {
                "opponent": next_matchup["opponent"],
                "result": "loss",
                "score": f"{game_result['team_score']} - {game_result['opponent_score']}",
                "period": game_result["period"],
                "team_stats": game_result["team_stats"],
                "opponent_stats": game_result["opponent_stats"]
            }
            game_log.append({
                "year": current_year,
                "week": current_week,
                "opponent": next_matchup["opponent"],
                "result": game_result["outcome"],
                "team_score": game_result["team_score"],
                "opponent_score": game_result["opponent_score"],
                "team_stats": game_result["team_stats"],
                "opponent_stats": game_result["opponent_stats"],
                "period": game_result["period"]
            })
            team_record["losses"] += 1
            next_matchup = None
        current_week += 1

    if current_week > 24:
        handle_offseason()
        return

    if next_matchup and current_week == next_matchup['week']:
        team_overall = sum([player['Overall'] for player in team]) // len(team) + random.randint(3, 5)
        game_result = simulate_game(team_overall, next_matchup['overall_rating'])

        if game_result["outcome"] == "win":
            team_record["wins"] += 1
        else:
            team_record["losses"] += 1

        game_log.append({
            "year": current_year,
            "week": current_week,
            "opponent": next_matchup["opponent"],
            "result": game_result["outcome"],
            "team_score": game_result["team_score"],
            "opponent_score": game_result["opponent_score"],
            "team_stats": game_result["team_stats"],
            "opponent_stats": game_result["opponent_stats"],
            "period": game_result["period"]
        })

        last_week_matchup = {
            "opponent": next_matchup["opponent"],
            "result": "win" if game_result["outcome"] == "win" else "loss",
            "score": f"{game_result['team_score']} - {game_result['opponent_score']}",
            "period": game_result["period"]
        }

    announce_upcoming_matchup(current_week + 1, teams_df)
    current_week += 1
    scouting_points = 3
    recruiting_points = 5




def handle_offseason():
    global team, committed_recruits, current_year, current_week, team_record, offseason_messages, user_team_info
    offseason_messages = []
    old_record = f"{team_record['wins']}-{team_record['losses']}" #updates old record and replaces the last years record line from last yseason
    user_team_info["record"] = old_record
    offseason_messages.append("--- Offseason ---")
    offseason_messages.append("Graduating senior players...")
    graduating = []
    for player in team:
        if player['Class'] == 'Senior' or player['Class'] == 'Redshirt Senior':
            graduating.append(player) #players graduate and get removed from the team
    for grad in graduating:
        offseason_messages.append(f"{grad['Name']} has graduated.")
        team.remove(grad)
    handle_player_progression()
    offseason_messages.append("Adding new recruits...")
    for recruit in committed_recruits: #appends recruits from the committed for next year to current team manaagement
        offseason_messages.append(f"Recruit {recruit['Name']} has joined your team.")
        team.append(recruit)
    committed_recruits.clear() #clears the committed recruits list
    team_record = {"wins": 0, "losses": 0} #resets team record
    current_year += 1
    current_week = 0
    recruits.clear()
    generate_recruits()
    offseason_messages.append("A new season begins! Good luck!")
    scheduled_opponents.clear()
    teams_df = load_team_data(api_link, year=2023) #keeps 2023 stats and just consistently uses that
    schedule = generate_schedule(teams_df, user_team_info["conference"], user_team_info["school"])
    save_season_to_csv(game_log, current_year)
    game_log.clear()
    game_menu()

def display_committed_recruits():

    global recruits, team, committed_recruits

    for recruit in recruits[:]:
        if recruit['Interest'] == 100 and recruit.get('scholarship_offered', False):
            print(f"{recruit['Name']} has committed to your team and is available this season.") #shows this message after a recruit commits (before week 1)
            team.append(recruit)
            recruits.remove(recruit)
        elif recruit in committed_recruits:
            print(f"{recruit['Name']} has committed and will join next season.") #shows this message after a recruit commits (week 1 or after)
            committed_recruits.remove(recruit)


def current_team_management():
    global committed_recruits
    print("\n--- Current Team Management ---")
    print("1. View Current Team Players")
    print("2. View Committed Recruits for Next Year")
    print("3. Redshirt a Player")
    print("4. Return to Game Menu")
    choice = input("Select an option: ")
    if choice == "1":
        for player in team: #shows all current players statistics and status
            redshirt_status = 'Yes' if player.get('Redshirted', False) else 'No' #updates redshirt status for those who are redshirted
            print(f"Overall: {player['Overall']}, Name: {player['Name']}, Age: {player['Age']}, Class: {player['Class']}, Height: {player['Height']}, Primary Position: {player['Primary Position']}, Shooting: {player['Shooting']}, Close Shot: {player['Close Shot']}, Defense: {player['Defense']}, Dribbling: {player['Dribbling']}, Passing: {player['Passing']}, Rebounding: {player['Rebounding']}, Athletic Ability: {player['Athletic Ability']}, Redshirted: {redshirt_status}")
        current_team_management()
    elif choice == "2":
        if committed_recruits: #shows appended recruits who are committed for next year
            print("\n--- Committed Recruits for Next Year ---")
            for recruit in committed_recruits:
                print(f"Overall: {recruit['Overall']}, Name: {recruit['Name']}, Age: {recruit['Age']}, Height: {recruit['Height']}, Primary Position: {recruit['Primary Position']}, Shooting: {recruit['Shooting']}, Close Shot: {recruit['Close Shot']}, Defense: {recruit['Defense']}, Dribbling: {recruit['Dribbling']}, Passing: {recruit['Passing']}, Rebounding: {recruit['Rebounding']}, Athletic Ability: {recruit['Athletic Ability']}")
        else:
            print("\nNo committed recruits yet.")
        current_team_management()
    elif choice == "3":
        redshirt_player()
    elif choice == "4":
        game_menu()
    else:
        print("Invalid choice. Please select again.")
        current_team_management()


def redshirt_player(): #redshirt function
    print("\n--- Redshirt a Player ---")
    eligible_players = [player for player in team if player['Class'] in ['Freshman', 'Sophomore', 'Junior', 'Senior'] and not player.get('Redshirted', False)] #filters teams and creates an eligible players list
    if not eligible_players:
        print("No players are eligible to be redshirted.") #if players are already redshirted they cannot be redshirted again and are not appended to eligible players list
        current_team_management()
        return
    for idx, player in enumerate(eligible_players, start=1): #loops through each eligible player
        print(f"{idx}. {player['Name']} - {player['Class']} - Age: {player['Age']}") #displayus their name, class, age for redshirt menu
    choice = input("Select a player to redshirt by number, or '0' to cancel: ")
    if choice.isdigit(): #checks to see if input is a valid input
        choice = int(choice) #converts users input (str) into INT for
        if choice == 0: #sends user back to team management menu
            current_team_management()
            return
        if 1 <= choice <= len(eligible_players): #player gets redshirted
            player = eligible_players[choice - 1]
            player['Redshirted'] = True
            print(f"{player['Name']} has been redshirted.")
        else:
            print("Invalid selection.")
    else:
        print("Invalid input.")
    current_team_management()


def recruit_menu():
    global scouting_points, recruiting_points, last_action_message

    while True: #clears screen after every input because recruit generation takes up 40 print lines (25 for recruit generation + other lines)
        clear_screen()

        if last_action_message:
            print(last_action_message)
            last_action_message = ""

        print("\n--- Recruiting Menu ---")
        print(f"Scouting Points Remaining: {scouting_points}")
        print(f"Recruiting Points Remaining: {recruiting_points}\n")

        for i, recruit in enumerate(recruits, start=1): #loops through each recruit and when a player is scouted, all their statistics are revealed
            if recruit['Scouted']:
                print(f"{i}. Overall: {recruit['Overall']}, Name: {recruit['Name']}, Age: {recruit['Age']}, Class: {recruit['Class']}, "
                      f"Height: {recruit['Height']}, Primary Position: {recruit['Primary Position']}, Interest: {recruit['Interest']}%, "
                      f"Shooting: {recruit['Shooting']}, Close Shot: {recruit['Close Shot']}, Defense: {recruit['Defense']}, Dribbling: {recruit['Dribbling']}, "
                      f"Passing: {recruit['Passing']}, Rebounding: {recruit['Rebounding']}, Athletic Ability: {recruit['Athletic Ability']}")
            else:
                print(f"{i}. {recruit['Name']} - {recruit['Primary Position']} - Interest: {recruit['Interest']}% (Scouting Required)")

        print("\nOptions:")
        print("1. Scout a recruit")
        print("2. Offer a scholarship to a recruit")
        print("3. Send Merch Package (+10% Interest)")
        print("4. Home Game Campus Visit (+20% Interest)")
        print("5. Campus Visit (+25% Interest)")
        print("6. Quit Menu")

        choice = input("\nSelect an option: ")
        if choice == "6":
            last_action_message = "Returning to the game menu."
            return
        elif choice in {"1", "2", "3", "4", "5"}:
            try:
                recruit_index = int(input("Enter the recruit number: ")) - 1
                if recruit_index < 0 or recruit_index >= len(recruits):
                    last_action_message = "Invalid recruit number. Please try again."
                    continue

                if choice == "1": #each recruit action has a different amount of interest that is added when the action is performed. (GOAL is to reach 100% for a recruit)
                    handle_recruit_action(recruit_index, "Scout")
                elif choice == "2":
                    handle_recruit_action(recruit_index, "Scholarship")
                elif choice == "3":
                    handle_recruit_action(recruit_index, "Merch Package", interest_increase=10)
                elif choice == "4":
                    handle_recruit_action(recruit_index, "Home Game Visit", interest_increase=20)
                elif choice == "5":
                    handle_recruit_action(recruit_index, "Campus Visit", interest_increase=25)
            except ValueError:
                last_action_message = "Invalid input. Please enter a number."
        else:
            last_action_message = "Invalid option. Please select a valid choice."

def handle_recruit_action(recruit_index, action_type, interest_increase=0):
    global recruiting_points, scouting_points, recruits, last_action_message, committed_recruit_messages, committed_recruits, team, current_week
    if not (0 <= recruit_index < len(recruits)): #checks to see if input matches a recruit value
        last_action_message = "Invalid recruit number. Please select a valid recruit."
        return
    recruit = recruits[recruit_index]
    if action_type == "Scout": #scout function
        if scouting_points <= 0:
            last_action_message = "No scouting points left."
        elif recruit['Scouted']:
            last_action_message = f"{recruit['Name']} has already been scouted."
        else:
            recruit['Scouted'] = True
            recruit['revealed_stats'] = ['Shooting', 'Close Shot', 'Defense', 'Dribbling', 'Passing', 'Rebounding', 'Athletic Ability'] #reveals stats
            scouting_points -= 1
            last_action_message = f"You scouted {recruit['Name']}."

    elif action_type == "Scholarship": #scholarship function
        if recruit['Interest'] < 100:
            last_action_message = f"{recruit['Name']} is not interested enough to offer a scholarship." #needs 100%
        elif recruit.get('scholarship_offered', False):
            last_action_message = f"{recruit['Name']} already has a scholarship offer." #needs offer
        elif recruiting_points > 0:
            recruit['scholarship_offered'] = True
            recruiting_points -= 1
            last_action_message = f"You offered a scholarship to {recruit['Name']}."
        else:
            last_action_message = "Not enough recruiting points to offer a scholarship." #need to wait to get more recruiting points

    elif action_type in ["Merch Package", "Home Game Visit", "Campus Visit"]: #interest increasing functions
        if recruiting_points <= 0:
            last_action_message = "Not enough recruiting points for this action."
        else:
            recruit['Interest'] = min(recruit['Interest'] + interest_increase, 100)
            recruiting_points -= 1
            last_action_message = f"{action_type} performed on {recruit['Name']}. Interest increased to {recruit['Interest']}%."

    if recruit['Interest'] == 100 and recruit.get('scholarship_offered', False): #appends recruits to either list
        if current_week == 0:
            team.append(recruit)
            recruits.remove(recruit)
            message = f"{recruit['Name']} committed to your team and is available this season!"
            last_action_message += " " + message
            committed_recruit_messages.append(message)
        else:
            committed_recruits.append(recruit)
            recruits.remove(recruit)
            message = f"{recruit['Name']} committed to your team for next year."
            last_action_message += " " + message
main_menu()