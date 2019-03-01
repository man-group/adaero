import { Component, Input, OnInit } from '@angular/core';
import { ApiService, NomineePayload, MessageTemplatePayload } from '../../../services/api.service';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-nominees-list',
  templateUrl: './nominees-list.component.html',
  styleUrls: ['./nominees-list.component.scss']
})
export class NomineesListComponent implements OnInit {
    constructor(public api: ApiService) {}

    data: Observable<{} | NomineePayload | MessageTemplatePayload>;

    ngOnInit() {
        this.data = this.api.getNominees();
    }
}
