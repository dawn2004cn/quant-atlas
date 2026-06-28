"""
Design Patterns Library for Quant Atlas
========================================

Creational Patterns (5):
1. Singleton - Single instance management
2. Factory Method - Object creation via subclasses
3. Abstract Factory - Family of related objects
4. Builder - Complex object construction
5. Prototype - Object cloning

Structural Patterns (7):
6. Adapter - Interface compatibility
7. Bridge - Abstraction/implementation separation
8. Composite - Tree structure management
9. Decorator - Dynamic behavior addition
10. Facade - Simplified interface
11. Flyweight - Shared objects
12. Proxy - Controlled access

Behavioral Patterns (11):
13. Chain of Responsibility - Request handling chain
14. Command - Request encapsulation
15. Iterator - Collection traversal
16. Mediator - Object communication
17. Memento - State capture
18. Observer - Event notification
19. State - State machine
20. Strategy - Algorithm selection
21. Template Method - Algorithm skeleton
22. Visitor - Operation on elements

Architectural Patterns (5):
23. Repository - Data access abstraction
24. Unit of Work - Transaction management
25. Service Layer - Business logic encapsulation
26. CQRS - Command/Query separation
27. Dependency Injection - Loose coupling

SOLID Principles:
- S: Single Responsibility
- O: Open/Closed
- L: Liskov Substitution
- I: Interface Segregation
- D: Dependency Inversion
"""

from .creational import *
from .structural import *
from .behavioral import *
from .architectural import *
