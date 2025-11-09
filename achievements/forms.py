from django import forms
from .models import Achievement


class AchievementForm(forms.ModelForm):
    class Meta:
        model = Achievement
        fields = ['title', 'category', 'subcategory', 'proof_file', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get('category')
        subcategory = cleaned.get('subcategory')
        description = cleaned.get('description')
        proof = cleaned.get('proof_file')

        if not proof:
            raise forms.ValidationError("Please upload a certificate or proof file.")


        if category not in ('other', None) and not subcategory:
            raise forms.ValidationError("Please choose a subcategory for this achievement.")


        if category == 'other' and not description:
            raise forms.ValidationError("For 'Other' category please describe the achievement.")

        return cleaned

