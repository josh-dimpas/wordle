from django.apps import apps
from django.db import connection
from django.forms import ValidationError
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from game.apps import GameConfig
from game.middleware import AccountAccessMiddleware
from game.models import Game
from game.services import WordService
from game.utils import generate_code

config: GameConfig = apps.get_app_config('game')

# Create your views here.
def index(request):
    return JsonResponse(
        { 
         "message": "Welcome to wordle API."
         " Login your account with /login"
         " Don't have an account yet? try /register."
         f" Start a game immediately now with /{config.ANON_USERNAME}/play"
         }
    )

@csrf_exempt
@AccountAccessMiddleware(match_username=True)
def play(request, username: str):

    game = Game.objects.create(
        code = generate_code(),
        word = WordService.get_random_word(),
        player = username
    )

    return JsonResponse({ 'game_code': game.code })

@csrf_exempt
@AccountAccessMiddleware(match_username=True)
def view_game(request, username: str, game_code: str):
    game = Game.objects.filter(code=game_code).first()

    if game is None:
        return JsonResponse({ "error": "Game code does not exist" }, status=404)

    if game.player != username:
        return JsonResponse({ "error": f"{username} do not have a game with code: {game_code}"})

    return JsonResponse(game.to_json())
        
@csrf_exempt
@AccountAccessMiddleware(match_username=True)
def guess(request, username: str, game_code: str, input: str):
    game = Game.objects.filter(code=game_code).first()

    if game is None:
        return JsonResponse({ "error": "Game code does not exist"}, status=404)

    if game.player != username:
        return JsonResponse({ "error": f"{username} do not have a game with code: {game_code}"})

    # Return an error if guess length is not equal with word length
    if len(input) != len(game.word):
        return JsonResponse({ "error": f"Please provide a word with matching length. You sent {len(input)}, required is {len(game.word)}"}, status=403)

    # Return a message when guessing a non-active game
    if game.is_win:
        return JsonResponse({ "message": f"Game has already won. Word is {game.word}."})
    
    if game.get_is_finished():
        return JsonResponse({ "message": f"You ran out of tries. Word is {game.word}."})

    game.guess(input)

    # TEMPORARY MESSAGES (should be handled by frontend)
    if game.word == input:
        return JsonResponse({ "message": f"You guessed correctly in just {len(game.tries)} tries! "})

    if game.get_tries_left() == 0:
        return JsonResponse({ "message": f"You ran out of tries. Word is {game.word}"})

    return JsonResponse(game.to_json())

@csrf_exempt
@AccountAccessMiddleware(match_username=False)
def account_stats(request: HttpRequest, username: str):
    offset = int(request.GET.get('offset', '0'))
    limit = int(request.GET.get('limit', '10'))
    order = request.GET.get('order', 'desc') 

    is_descending =  order == 'desc' 

    try :
        if username == config.ANON_USERNAME:
            return JsonResponse({ "message": "No stats for anon"})

        # Get all games with that player
        games = Game.objects.filter(player=username).order_by(f'{'-' if is_descending else ''}created_at')[offset : offset + limit]
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

@csrf_exempt
def leaderboards(request: HttpRequest):
    offset = int(request.GET.get('offset', '0'))
    limit = int(request.GET.get('limit', '10'))
    order = request.GET.get('order', 'desc') 

    is_descending = order == 'desc'

    # Get all games grouped by players
    query = f"""
    SELECT
        g.player,
        COUNT(CASE WHEN g.is_win = TRUE THEN 1 END) as games_won,
        COUNT(*) AS games_played
    FROM game_game AS g
    WHERE g.player != '{config.ANON_USERNAME}'
    GROUP BY g.player
    ORDER BY games_won {'DESC' if is_descending else 'ASC'}
    LIMIT {limit}
    {'' if offset == 0 else f"OFFSET {offset}"}
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