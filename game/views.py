from django.apps import apps
from django.db import connection
from django.forms import ValidationError
from django.http import HttpRequest, JsonResponse

from game.apps import GameConfig
from game.models import Game
from game.services import WordService
from game.utils import generate_code, get_user

config: GameConfig = apps.get_app_config('game')

# Create your views here.
def index(request):
    return JsonResponse(
        { 
         "message": "Welcome to wordle API.\n"
         "Login with your account at /login\n"
         "Don't have an account yet? try /register.\n"
         f"Start a game immediately now with /{config.ANON_USERNAME}"
         }
    )

def try_get_user(request: HttpRequest):
    username = request.resolver_match.kwargs.get('username')

    if not config.ENABLE_AUTH:
        return 

    if username is None:
        raise ValueError("Username is required")

    if username == config.ANON_USERNAME:
        return None
    
    user = get_user(request)
    if user is None:
        raise ValidationError("Invalid JWT Token")

    return user


# NOTE: test game code: jnC5pG
def play(request, username: str):
    # TODO: Use middleware for authentication
    try :
        try_get_user(request)
    except BaseException as e:
        return JsonResponse({ "error": e }, status = 401)

    game = Game.objects.create(
        code = generate_code(),
        word = WordService.get_random_word(),
        player = username
    )
    return JsonResponse({ 'game_code': game.code })

def view_game(request, username: str, game_code: str):
    # TODO: Use middleware for authentication
    try :
        try_get_user(request)
    except BaseException as e:
        return JsonResponse({ "error": e }, status = 401)

    game = Game.objects.filter(code=game_code).first()

    if game is None:
        return JsonResponse({ "error": "Game code does not exist" }, status=404)

    return JsonResponse(game.to_json())
        

def guess(request, username: str, game_code: str, input: str):
    try :
        try_get_user(request)
    except ValidationError as e:
        return JsonResponse({ "error": e.message }, status = 401)

    game = Game.objects.filter(code=game_code).first()

    if game is None:
        return JsonResponse({ "error": "Game code does not exist"}, status=404)

    # Return an error if guess length is not equal with word length
    if len(input) != len(game.word):
        return JsonResponse({ "error": f"Please provide a word with matching length. You sent {len(input)}, required is {len(game.word)}"}, status=403)

    # Return a message when guessing a non-active game
    if game.is_win:
        return JsonResponse({ "message": f"Game has already won. Word is {game.word}."})
    
    if game.get_is_active():
        return JsonResponse({ "message": f"You ran out of tries. Word is {game.word}."})

    game.guess(input)

    # TEMPORARY MESSAGES (should be handled by frontend)
    if game.word == input:
        return JsonResponse({ "message": f"You guessed correctly in just {len(game.tries)} tries! "})

    if game.get_tries_left() == 0:
        return JsonResponse({ "message": f"You ran out of tries. Word is {game.word}"})

    return JsonResponse(game.to_json())

# TODO: Add search parameters for games list pagination
def account_stats(request, username: str):
    try :
        if username is config.ANON_USERNAME:
            return JsonResponse({ "message": "No stats for anon"})

        try_get_user(request)

        # Get all games with that player
        games = Game.objects.filter(player=username)
        won_games = [obj for obj in games if obj.is_win]

        return JsonResponse({
            "games_played": len(games),
            "games_won": len(won_games),
            "games": [
                {
                    "code": g.code,
                    "won": g.is_win,
                    "tries_left": g.get_tries_left(),
                    "created_at": g.created_at,
                } for g in games
            ]
        })
    except ValidationError as e:
        return JsonResponse({ "error": e.message }, status = 401)

    except BaseException as e:
        return JsonResponse({ "error": e }, status = 401)

def leaderboards(request):
    # Get all games grouped by players
    query = f"""
    SELECT
        g.player,
        COUNT(CASE WHEN g.is_win = TRUE THEN 1 END) as games_won,
        COUNT(*) AS games_played
    FROM game_game AS g
    WHERE g.player != '{config.ANON_USERNAME}'
    GROUP BY g.player
    ORDER BY games_won DESC
    """

    with connection.cursor() as cursor:
        cursor.execute(query)

        columns = [col[0] for col in cursor.description]
        players = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

        print(players)
        return JsonResponse(players, safe=False)
        

    
