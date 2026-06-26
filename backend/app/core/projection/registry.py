from app.core.projection.projector import Projector


class ProjectionRegistry:
    def __init__(self):
        self._projectors: dict[str, Projector] = {}

    def register(self, projector: Projector):
        if projector.name in self._projectors:
            raise ValueError(f"Projector {projector.name} already registered.")
        self._projectors[projector.name] = projector

    def discover(self) -> list[Projector]:
        """Returns projectors topologically sorted by dependencies."""
        visited = set()
        temp_mark = set()
        order = []

        def visit(n: str):
            if n in temp_mark:
                raise Exception("Cyclic dependency detected in projectors")
            if n not in visited:
                temp_mark.add(n)
                if n in self._projectors:
                    for dep in self._projectors[n].dependencies:
                        visit(dep)
                temp_mark.remove(n)
                visited.add(n)
                if n in self._projectors:
                    order.append(self._projectors[n])

        for name in self._projectors:
            if name not in visited:
                visit(name)

        return order

    def versions(self) -> dict[str, int]:
        return {p.name: p.version for p in self._projectors.values()}

    def projection_groups(self) -> list[str]:
        return list(set(p.projection_group for p in self._projectors.values()))

    def supported_events(self) -> list[str]:
        events = set()
        for p in self._projectors.values():
            events.update(p.supported_events)
        return list(events)

    def dependencies(self) -> dict[str, list[str]]:
        return {p.name: p.dependencies for p in self._projectors.values()}

    def get_projectors_for_event(self, event_type: str) -> list[Projector]:
        # Return in dependency-sorted order
        return [p for p in self.discover() if event_type in p.supported_events or "*" in p.supported_events]

projector_registry = ProjectionRegistry()
