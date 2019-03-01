import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { SummariseFeedbackComponent } from './summarise-feedback.component';

describe('SummariseFeedbackComponent', () => {
  let component: SummariseFeedbackComponent;
  let fixture: ComponentFixture<SummariseFeedbackComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ SummariseFeedbackComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(SummariseFeedbackComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
