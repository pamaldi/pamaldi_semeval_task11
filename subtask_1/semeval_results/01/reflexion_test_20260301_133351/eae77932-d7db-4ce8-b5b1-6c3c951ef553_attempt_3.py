% Case A: Syllogism is INVALID due to undistributed middle
% Strategy: Build a counterexample where premises are true but conclusion is false

% Witness: A white pencil (satisfies "Some pencils are white")
pencil(white_pencil1).
white(white_pencil1).

% Witness: A white sheet of paper (satisfies "Some sheets of paper are not white" through negation)
paper(white_paper1).
white(white_paper1).

% Fail clauses for terms not explicitly defined
pencil(_) :- fail.
paper(_) :- fail.
white(_) :- fail.

% Validity check: Some sheets of paper are not pencils (should FAIL in this model)
valid_syllogism :- paper(X), \+ pencil(X).