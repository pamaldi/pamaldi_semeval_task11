% Witness: a white pencil
pencil(white_pencil1).
white(white_pencil1).

% Witness: a sheet of paper that is NOT white
paper(non_white_paper1).

% Fail clause for pencils (no additional pencils in this model)
pencil(_) :- fail.

% Fail clause for white (not all entities are white)
white(_) :- fail.

% Validity check: Some sheets of paper are not pencils
valid_syllogism :- paper(X), \+ pencil(X).