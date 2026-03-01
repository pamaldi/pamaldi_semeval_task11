% Witnesses for I-propositions
has_degree(anna).
works_in_school(anna).

works_in_school(bob).
is_teacher(bob).

% A-premise: Some individuals who have degrees are people who work in schools.
% Encoded as facts for has_degree/1 and works_in_school/1

% A-premise: Some person who works in a school is a teacher.
% Encoded as facts for works_in_school/1 and is_teacher/1

% Conclusion: Some teachers are individuals with degrees.
% Validity check: does there exist a teacher who has a degree?

valid_syllogism :- is_teacher(X), has_degree(X).