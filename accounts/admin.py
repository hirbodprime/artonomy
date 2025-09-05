from django.contrib import admin
from .models import (
    Category, User, UserCategory, SkillTag, Profile, SocialLink,
    PersonalValue, HobbyInterest, Achievement, Goal, FunFact,
    Education, Experience, Book, Certification, Course, Project, Award,PublicNumberCounter
)




# -------------------------
# Inlines
# -------------------------
class UserCategoryInline(admin.TabularInline):
    model = UserCategory
    extra = 1


class SocialLinkInline(admin.TabularInline):
    model = SocialLink
    extra = 1


class AchievementInline(admin.TabularInline):
    model = Achievement
    extra = 1


class GoalInline(admin.TabularInline):
    model = Goal
    extra = 1


class FunFactInline(admin.TabularInline):
    model = FunFact
    extra = 1


class EducationInline(admin.TabularInline):
    model = Education
    extra = 1


class ExperienceInline(admin.TabularInline):
    model = Experience
    extra = 1


class ProjectInline(admin.TabularInline):
    model = Project
    extra = 1


# -------------------------
# Main Admin Models
# -------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "role", "is_staff", "is_superuser", "public_code", "public_number")
    list_filter = ("role", "is_staff", "is_superuser")
    search_fields = ("username", "email", "public_code", "public_number")
    inlines = [UserCategoryInline]


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "phone")
    search_fields = ("user__username", "user__email", "title", "phone")
    inlines = [
        SocialLinkInline, AchievementInline, GoalInline,
        FunFactInline, EducationInline, ExperienceInline, ProjectInline
    ]
    filter_horizontal = ("skills",)


@admin.register(SkillTag)
class SkillTagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ("profile", "kind", "label", "url")
    search_fields = ("label", "url")
    list_filter = ("kind",)


@admin.register(PersonalValue)
class PersonalValueAdmin(admin.ModelAdmin):
    list_display = ("profile", "name")
    search_fields = ("name",)


@admin.register(HobbyInterest)
class HobbyInterestAdmin(admin.ModelAdmin):
    list_display = ("profile", "name")
    search_fields = ("name",)


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("profile", "title", "date")
    search_fields = ("title", "description")
    list_filter = ("date",)


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("profile", "title", "date")
    search_fields = ("title", "description")
    list_filter = ("date",)


@admin.register(FunFact)
class FunFactAdmin(admin.ModelAdmin):
    list_display = ("profile", "text")
    search_fields = ("text",)


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ("profile", "school", "degree", "location", "period_label")
    search_fields = ("school", "degree", "location")
    list_filter = ("is_current",)


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ("profile", "title", "company", "location", "period_label")
    search_fields = ("company", "title", "location")
    list_filter = ("is_current",)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("profile", "title", "author", "year")
    search_fields = ("title", "author", "year")


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ("profile", "name", "issuer", "issue_date")
    search_fields = ("name", "issuer")
    list_filter = ("issue_date",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("profile", "name", "org", "date")
    search_fields = ("name", "org")
    list_filter = ("date",)



@admin.register(PublicNumberCounter)
class PublicNumberCounterAdmin(admin.ModelAdmin):
    list_display = ("name", "last_number")
    list_editable = ("last_number",)
    search_fields = ("name",)
    ordering = ("name",)

    def has_add_permission(self, request):
        """Allow adding only if no object exists (singleton pattern)."""
        if PublicNumberCounter.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        """Optional: prevent deletion (singleton safety)."""
        return False

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("profile", "title", "employer", "period_label")
    search_fields = ("title", "employer", "description", "tech_stack")
    list_filter = ("is_current",)


@admin.register(Award)
class AwardAdmin(admin.ModelAdmin):
    list_display = ("profile", "title", "organization", "date")
    search_fields = ("title", "organization")
    list_filter = ("date",)
