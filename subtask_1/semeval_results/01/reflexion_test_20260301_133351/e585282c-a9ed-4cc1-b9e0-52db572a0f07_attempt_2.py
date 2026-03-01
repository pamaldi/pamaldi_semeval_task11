% Facts for chess and tag
chess(chess1).
tag(tag1).

% Rule from first premise (All chess are board games)
board_game(X) :- chess(X).

% Fail clause for board_game (since only chess is a board game and tag is never a board game)
board_game(X) :- fail.

% Validity check for conclusion: tag is not chess
valid_syllogism :- tag(X), \+ chess(X).