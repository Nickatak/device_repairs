"""Bench work — Repair (phase-tracked engagement) and its contents: Note, Measurement, Part, Media."""

from django.core.exceptions import ValidationError
from django.db import models

from .inventory import Device


class Repair(models.Model):
    """One diagnose-and-fix engagement on one Device. Aggregate root of the log.

    Bench work moves through a FIXED phase track (2026-07-21 redesign):
    Teardown → Wash → Repair → Re-assemble → Verify. Each phase is a done-timestamp +
    optional deviation note; phases are skippable (a diagnosis-only job never washes).
    Freeform Notes + Measurements are the *contents of the Repair phase* — the one
    phase that's genuinely variable. Per-screw granularity belongs to the (parked)
    per-model teardown guide, not the log. The track ends at Verify: outflow states
    (listed / sold / shipped) are Device-lifecycle facts, not repair phases.

    No status field (removed 2026-07-21): the phase track IS the repair's state;
    the lifecycle lives on Device. A Repair exists only when bench work starts —
    never as a status carrier.

    `completed_at` is MANUAL and comes after Verify: marking a repair completed with
    phases unchecked is a deliberate, demonstrable statement that those phases did
    NOT happen (stopped before re-assembly, say) — not an oversight. Completion
    never requires checking everything.
    """

    PHASES = [
        ("teardown", "Teardown"),
        ("wash", "Wash"),
        ("repair", "Repair"),
        ("reassemble", "Re-assemble"),
        ("verify", "Verify"),
    ]

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="repairs")
    comment = models.TextField(blank=True, help_text="Repair-level commentary (distinct from notes).")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Manual completion mark, after Verify. Unchecked phases on a completed "
            "repair demonstrably did NOT happen."
        ),
    )

    teardown_done_at = models.DateTimeField(null=True, blank=True)
    teardown_note = models.TextField(blank=True, help_text="Deviations only — the routine is not logged.")
    wash_done_at = models.DateTimeField(null=True, blank=True)
    wash_note = models.TextField(blank=True)
    repair_done_at = models.DateTimeField(null=True, blank=True)
    repair_note = models.TextField(blank=True, help_text="Summary only — the detail lives in Steps.")
    reassemble_done_at = models.DateTimeField(null=True, blank=True)
    reassemble_note = models.TextField(blank=True)
    verify_done_at = models.DateTimeField(null=True, blank=True)
    verify_note = models.TextField(blank=True, help_text="Function-validation evidence (tests run, results).")

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # Every repair carries a standing "Measurements" note (position 0) — the
        # bucket for readings that belong to no specific notation. There's almost
        # always at least a bundle of measurements (Nick, 2026-07-21).
        created = self.pk is None
        super().save(*args, **kwargs)
        if created:
            self.notes.create(position=0, title="Measurements")

    @property
    def current_phase(self):
        """Where the track stands: the phase after the last checked one.

        'complete' ONLY when completed_at is set (manual). 'completion' = phases
        exhausted but not yet marked — the next action is the mark itself. Skips
        count as done-with-nothing-to-say: with teardown and repair done but wash
        blank, the bench has moved on — current is re-assemble, not wash.
        """
        if self.completed_at:
            return "complete"
        keys = [key for key, _ in self.PHASES]
        done = [i for i, key in enumerate(keys) if getattr(self, f"{key}_done_at")]
        start = done[-1] + 1 if done else 0
        return keys[start] if start < len(keys) else "completion"

    def __str__(self):
        return f"Repair #{self.pk} — {self.device}"


class Note(models.Model):
    """The spine: one notation within a Repair, ordered. (Renamed from Step 2026-07-21.)

    Untyped: the old Type enum (test / observation / repair / notation) collapsed —
    a test produces an observation, logging it makes it a notation, and a corrective
    entry is equally a notation of work done (the phase track already marks that
    repair work happened). A note is a dated entry: title, text, measurements.
    Sub-notes allowed ONE level deep; deeper nesting means the approach went wrong.
    """

    repair = models.ForeignKey(Repair, on_delete=models.CASCADE, related_name="notes")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="subnotes"
    )
    position = models.PositiveIntegerField(
        default=0, help_text="Ordering within the repair (or within a parent note)."
    )
    title = models.CharField(max_length=255, blank=True, help_text="Short heading for the note.")
    text = models.TextField(
        blank=True, help_text="The notation — what was tested / observed / done."
    )
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True, help_text="Note-scoped side commentary.")

    class Meta:
        ordering = ["position", "id"]

    def clean(self):
        if self.parent_id:
            if self.parent_id == self.pk:
                raise ValidationError("A note cannot be its own parent.")
            if self.parent.parent_id:
                raise ValidationError(
                    "Notes nest only one level deep — a sub-note cannot have sub-notes."
                )
            if self.parent.repair_id != self.repair_id:
                raise ValidationError("A sub-note must belong to the same repair as its parent.")

    def __str__(self):
        return self.title or self.text[:50]


class Measurement(models.Model):
    """Quick bench annotation on a Note: what was measured, and what it read.

    Simplified 2026-07-21 from the original structured shape (FK label lookup +
    decimal value + unit FK + expected nominal) — same grain-shift as the phase
    track: skill growth made free text the working unit. '5V rail' / '4.98 V'
    typed fast beats a four-field form. A failed measurement = the story in
    `value` or `comment` ('no reading — pad lifted').
    """

    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="measurements")
    what = models.CharField(
        max_length=200, help_text="What was measured — '5V rail', 'C701 ESR', 'DC jack'."
    )
    value = models.CharField(
        max_length=120,
        blank=True,
        help_text="What it read — '4.98 V', '120 mΩ', 'no reading — pad lifted'.",
    )
    comment = models.TextField(
        blank=True, help_text="The 'why', or a provisional conclusion."
    )

    def __str__(self):
        return f"{self.what}: {self.value or '—'}"


class Part(models.Model):
    """Consumed into the board at a Note; counts toward the device's parts cost.

    A corrective note may record consumed Parts or none at all — 'fix' != 'install a part'.
    """

    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="parts")
    name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"{self.quantity}× {self.name}"


class Media(models.Model):
    """Before/after & condition photos. Attaches to EITHER a Repair OR a Note (exactly one).

    The load-bearing case is condition documentation — photograph a pre-existing defect on
    intake so a later 'they broke my screen' claim is answered with the intake photo.
    """

    image = models.ImageField(upload_to="repair_media/")
    caption = models.CharField(max_length=255, blank=True)
    repair = models.ForeignKey(
        Repair, null=True, blank=True, on_delete=models.CASCADE, related_name="media"
    )
    note = models.ForeignKey(
        Note, null=True, blank=True, on_delete=models.CASCADE, related_name="media"
    )

    class Meta:
        verbose_name_plural = "media"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(repair__isnull=False, note__isnull=True)
                    | models.Q(repair__isnull=True, note__isnull=False)
                ),
                name="media_attaches_to_exactly_one_parent",
            )
        ]

    def clean(self):
        if bool(self.repair_id) == bool(self.note_id):
            raise ValidationError("Media must attach to exactly one of: a repair OR a note.")

    def __str__(self):
        return self.caption or f"Media #{self.pk}"
