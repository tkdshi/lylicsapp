from django import forms

class LylicForm(forms.Form):
    lylic = forms.CharField(lavel="歌詞",widget=forms.Textarea)