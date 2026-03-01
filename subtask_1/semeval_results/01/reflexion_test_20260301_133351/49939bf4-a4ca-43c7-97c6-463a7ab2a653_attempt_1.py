% Witness: a student who is also a person
student(alice).
person(alice).

% person has NO facts besides from student
person(X) :- student(X).

% robot has NO facts and is disjoint from person
robot(_) :- fail.

% Validity check
valid_syllogism :- \+ (robot(X), student(X)).