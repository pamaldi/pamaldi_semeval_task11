% Facts
board_game(chess1).
tag(tag1).

% Fail clause for board_game (since only chess is a board game)
board_game(X) :- fail.

% Rule from first premise (All chess are board games)
board_game(X) :- chess(X).

% Validity check for conclusion: tag is not chess
valid_syllogism :- tag(X), \+ chess(X).