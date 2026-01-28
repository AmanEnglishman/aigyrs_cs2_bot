from faceit_client import search_player, get_player_stats
import json

nickname = "electroveniB"

player = search_player(nickname)
stats = get_player_stats(player["player_id"], game="cs2")

print(json.dumps(stats, indent=2, ensure_ascii=False))